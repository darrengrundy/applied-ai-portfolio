"""Asynchronous Microsoft Foundry chat client with conversation context."""

import asyncio
import os

from azure.identity.aio import DefaultAzureCredential, get_bearer_token_provider
from dotenv import load_dotenv
from openai import AsyncOpenAI


def require_setting(name: str) -> str:
    """Return a required environment setting or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment setting: {name}")
    return value


async def main() -> None:
    load_dotenv()
    endpoint = require_setting("AZURE_OPENAI_ENDPOINT")
    deployment = require_setting("MODEL_DEPLOYMENT")

    credential = DefaultAzureCredential()
    try:
        token_provider = get_bearer_token_provider(
            credential,
            "https://ai.azure.com/.default",
        )
        client = AsyncOpenAI(base_url=endpoint, api_key=token_provider)
        previous_response_id = None

        while True:
            prompt = input('\nEnter a prompt (or type "quit" to exit): ').strip()
            if prompt.lower() == "quit":
                break
            if not prompt:
                print("Please enter a prompt.")
                continue

            response = await client.responses.create(
                model=deployment,
                instructions=(
                    "You are a helpful AI assistant that answers questions and "
                    "provides information."
                ),
                input=prompt,
                previous_response_id=previous_response_id,
            )
            print("Assistant:", response.output_text)
            previous_response_id = response.id
    finally:
        await credential.close()


if __name__ == "__main__":
    asyncio.run(main())
