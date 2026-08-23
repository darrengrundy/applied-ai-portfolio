"""Synchronous Microsoft Foundry chat client with context and streaming."""

import os

from dotenv import load_dotenv
from openai import OpenAI


def require_setting(name: str) -> str:
        """Return a required environment setting or raise a clear error."""
        value = os.getenv(name)
        if not value:
                    raise ValueError(f"Missing required environment setting: {name}")
                return value


def build_client(endpoint: str) -> OpenAI:
        """Return an OpenAI client using API key or DefaultAzureCredential."""
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if api_key:
                return OpenAI(base_url=endpoint, api_key=api_key)

    # Fall back to Entra ID token (requires az login or managed identity)
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider

    token_provider = get_bearer_token_provider(
                DefaultAzureCredential(),
                "https://ai.azure.com/.default",
    )
    return OpenAI(base_url=endpoint, api_key=token_provider)


def main() -> None:
        load_dotenv()
    endpoint = require_setting("AZURE_OPENAI_ENDPOINT")
    deployment = require_setting("MODEL_DEPLOYMENT")

    client = build_client(endpoint)
    previous_response_id = None

    while True:
                prompt = input('\nEnter a prompt (or type "quit" to exit): ').strip()
                if prompt.lower() == "quit":
                                break
                            if not prompt:
                                            print("Please enter a prompt.")
                                            continue

        stream = client.responses.create(
                        model=deployment,
                        instructions=(
                                            "You are a helpful AI assistant that answers questions and "
                                            "provides information."
                        ),
                        input=prompt,
                        previous_response_id=previous_response_id,
                        stream=True,
        )

        for event in stream:
                        if event.type == "response.output_text.delta":
                                            print(event.delta, end="", flush=True)
elif event.type == "response.completed":
                previous_response_id = event.response.id
        print()


if __name__ == "__main__":
        main()
