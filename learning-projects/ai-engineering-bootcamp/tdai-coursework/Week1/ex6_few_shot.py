"""
Exercise: Few-Shot Prompting
This script demonstrates how to guide the model with a few examples (shots) to establish a pattern.
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

def demo_few_shot(user_query):
    print(f"\n--- Few-Shot Prompting Demo ---")
    # We provide 3 'shots' (examples) to establish the pattern
    messages = [
        {"role": "system", "content": "You convert human requests into RobotCommand format."},
        # Shot 1
        {"role": "user", "content": "Pick up the red ball"},
        {"role": "assistant", "content": "ACTION: GRAB | OBJ: BALL | COLOR: RED"},
        # Shot 2
        {"role": "user", "content": "Move to the kitchen quickly"},
        {"role": "assistant", "content": "ACTION: NAVIGATE | DEST: KITCHEN | SPEED: HIGH"},
        # Shot 3
        {"role": "user", "content": "Open the blue door slowly"},
        {"role": "assistant", "content": "ACTION: ACTUATE | OBJ: DOOR | COLOR: BLUE | SPEED: LOW"},
        # The actual task (The 'Test' instance)
        {"role": "user", "content": user_query}
    ]
    response = client.chat.completions.create(
        model=DEPLOYMENT_NAME,
        messages=messages
    )
    print(f"Input: {user_query}")
    print(f"Few-Shot Output: {response.choices[0].message.content}")

if __name__ == "__main__":
    demo_few_shot("Throw the green cube at medium speed")
