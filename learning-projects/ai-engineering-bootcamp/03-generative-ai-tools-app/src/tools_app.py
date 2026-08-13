"""Travel assistant using Foundry-hosted web and file search tools."""

import glob
import os
from contextlib import ExitStack

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import OpenAI


def require_setting(name: str) -> str:
    """Return a required environment setting or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment setting: {name}")
    return value


def main() -> None:
    load_dotenv()
    endpoint = require_setting("AZURE_OPENAI_ENDPOINT")
    deployment = require_setting("MODEL_DEPLOYMENT")

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(),
        "https://ai.azure.com/.default",
    )
    client = OpenAI(base_url=endpoint, api_key=token_provider)

    brochure_paths = glob.glob("brochures/*.pdf")
    if not brochure_paths:
        raise FileNotFoundError(
            "No PDF files were found in brochures/. Use authorised local "
            "documents; course PDFs are not redistributed in this portfolio."
        )

    print("Creating a temporary vector store and uploading brochures...")
    vector_store = client.vector_stores.create(name="travel-brochures")

    try:
        with ExitStack() as stack:
            brochure_streams = [
                stack.enter_context(open(path, "rb")) for path in brochure_paths
            ]
            batch = client.vector_stores.file_batches.upload_and_poll(
                vector_store_id=vector_store.id,
                files=brochure_streams,
            )

        if batch.file_counts.failed:
            raise RuntimeError(
                f"{batch.file_counts.failed} brochure file(s) failed to upload."
            )
        print(f"Vector store ready with {batch.file_counts.completed} file(s).")

        previous_response_id = None
        while True:
            prompt = input('\nEnter a question (or type "quit" to exit): ').strip()
            if prompt.lower() == "quit":
                break
            if not prompt:
                print("Please enter a question.")
                continue

            response = client.responses.create(
                model=deployment,
                instructions=(
                    "You are a travel assistant that provides information on "
                    "services available from Margie's Travel. Use the supplied "
                    "brochures for company offerings and web search for general "
                    "destination information or current travel advice."
                ),
                input=prompt,
                previous_response_id=previous_response_id,
                tools=[
                    {
                        "type": "file_search",
                        "vector_store_ids": [vector_store.id],
                    },
                    {"type": "web_search"},
                ],
            )
            print(response.output_text)
            previous_response_id = response.id
    finally:
        client.vector_stores.delete(vector_store.id)
        print("Temporary vector store deleted.")


if __name__ == "__main__":
    main()
