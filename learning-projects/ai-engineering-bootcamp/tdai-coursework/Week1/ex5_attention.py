"""
Exercise: Attention Mechanism
This script demonstrates how LLMs use context to resolve ambiguous references (like 'it').
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# Get config from environment variables
ENDPOINT_URL = os.getenv("ENDPOINT_URL")
DEPLOYMENT_NAME = os.getenv("DEPLOYMENT_NAME")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")

# Initialize Azure AI Foundry client (OpenAI-compatible v1 endpoint)
client = OpenAI(
    base_url=ENDPOINT_URL,
    api_key=AZURE_OPENAI_API_KEY
)

def demo_attention(sentence):
    print(f"\n--- Attention Mechanism Demo ---")
    print(f"Sentence: \"{sentence}\"")
    prompt = (
        f"In the sentence: '{sentence}', which specific noun does the word 'it' refer to? "
        "Briefly explain how the adjectives in the sentence forced you to pay attention to that noun over others."
    )
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[{"role": "user", "content": prompt}]
    )
    print(f"AI Analysis:\n{response.choices[0].message.content}")

if __name__ == "__main__":
    # Demo 1: 'it' = animal
    demo_attention("The animal didn't cross the street because it was too tired.")
    # Demo 2: 'it' = street
    demo_attention("The animal didn't cross the street because it was too wide.")
