
import os
from openai import OpenAI

# Load environment variables (use a .env file in development)
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

def explain_llm(user_input):
    print(f"\n--- LLM Logic Demo ---")
    print(f"Input: \"{user_input}\"")
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=[
            {"role": "system", "content": "You are an assistant "},
            {"role": "user", "content": f"Complete this: {user_input}"}
        ]
    )
    print(f"LLM Response:\n{response.choices[0].message.content}")

if __name__ == "__main__":
    # Test the 'Autocomplete' nature
    explain_llm("Who won the gold medal?")
