"""
Demo: Calling a Local LLM via REST API (LM Studio)
This script sends a prompt to a local model running in LM Studio and prints the response.
"""
import requests
import json

# LM Studio API endpoint (default)
API_URL = "http://localhost:1234/api/v1/chat"

# Model and prompt details
MODEL_NAME = "liquid/lfm2.5-1.2b"
SYSTEM_PROMPT = "You answer only in rhymes."
USER_INPUT = "What is your favorite color?"

# Prepare the request payload
payload = {
    "model": MODEL_NAME,
    "system_prompt": SYSTEM_PROMPT,
    "input": USER_INPUT
}

headers = {"Content-Type": "application/json"}

# Send the request to the local LLM
response = requests.post(API_URL, headers=headers, data=json.dumps(payload))

# Handle and print the response
if response.status_code == 200:
    result = response.json()
    print("--- LLM Studio Response ---")
    print(result)
    # If the response has a specific field for the output, print it nicely
    if "output" in result:
        print("\nModel Output:")
        print(result["output"])
else:
    print(f"Error: {response.status_code}")
    print(response.text)
