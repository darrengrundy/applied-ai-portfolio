"""
Exercise: Hallucination in LLMs

What is Hallucination?
----------------------
In the context of Large Language Models (LLMs), "hallucination" refers to the model generating information that sounds plausible but is actually false, misleading, or entirely made up. This can happen when the model is asked about topics it was not trained on, or when it is prompted to be more creative (e.g., with a higher temperature setting).

Why does it happen?
- LLMs generate text by predicting the next word based on patterns in their training data, not by fact-checking.
- When asked about fictional or obscure topics, the model may "fill in the gaps" with invented details.
- Higher temperature settings make the model more random and creative, increasing the chance of hallucination.

This script demonstrates hallucination by asking the model about a made-up event, and shows how varying the temperature affects the output.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# Get config from environment variables
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME", "gpt-4o-mini")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize Azure AI Foundry client (OpenAI-compatible v1 endpoint)
client = OpenAI(
    base_url=ENDPOINT_URL,
    api_key=AZURE_OPENAI_API_KEY
)


def demonstrate_hallucination(fake_topic, temperature):
    """
    Prompts the model about a fake topic and prints the output.
    The temperature parameter controls the model's creativity:
      - Low temperature (e.g., 0.2): More factual, less creative
      - High temperature (e.g., 1.0): More creative, more likely to hallucinate
    """
    print(f"\n--- Hallucination Demo (temperature={temperature}) ---")
    print(f"Prompting the model about: {fake_topic}")
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "You are a helpful historian. Provide detailed facts."},
            {"role": "user", "content": f"Tell me about the historical significance of the {fake_topic}."}
        ],
        temperature=temperature
    )
    print(f"\nModel Output:\n{response.choices[0].message.content}")

# We provide a completely made-up event
if __name__ == "__main__":
    # Try with low and high temperature to see the difference
    demonstrate_hallucination("Great Marshmallow Treaty of 1724", temperature=0.2)
    print("\n" + "="*60 + "\n")
    demonstrate_hallucination("Great Marshmallow Treaty of 1724", temperature=1.0)
