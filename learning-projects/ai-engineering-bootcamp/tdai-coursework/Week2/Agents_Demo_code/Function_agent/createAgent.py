import os
import re
import sys
import json
import time
import requests
from openai import AzureOpenAI
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv, find_dotenv
from user_functions import (
    weather_tool_definition,
    fetch_weather
)

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode characters like ° printed below; force UTF-8 stdout.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# -------------------------------------------------------
# Environment
# -------------------------------------------------------
script_dir = os.path.dirname(os.path.abspath(__file__))
dotenv_path = os.path.join(script_dir, "..", ".env")
load_dotenv(dotenv_path)

AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://tdai-foundry.cognitiveservices.azure.com/"
)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT = os.getenv("DEPLOYMENT_NAME_GPT_4_mini", "gpt-4o-mini")
FOUNDRY_DEPLOYMENT = os.getenv("DEPLOYMENT_NAME_FOUNDRY", "gpt-5.2")
STUDENT_NAME = os.getenv("STUDENT_NAME", "student")
FOUNDRY_PROJECT_ENDPOINT = os.getenv(
    "FOUNDRY_PROJECT_ENDPOINT",
    "https://tdai-foundry.services.ai.azure.com/api/projects/tdai-foundry-project"
)

# -------------------------------------------------------
# Foundry Project API — creates agent visible in portal
# -------------------------------------------------------
# The Agents/Projects control plane doesn't support key-based auth
# ("Key-based authentication is not supported for this route") — it
# requires an Entra ID bearer token, unlike the data-plane OpenAI
# endpoint below which does accept an api-key.
foundry_token = DefaultAzureCredential().get_token("https://ai.azure.com/.default").token
foundry_headers = {"Authorization": f"Bearer {foundry_token}", "Content-Type": "application/json"}
normalized_student_name = re.sub(r'[^a-zA-Z0-9-]', '-', STUDENT_NAME).strip('-')
agent_name = f"weather-agent-{normalized_student_name}"

agent_payload = {
    "name": agent_name,
    "definition": {
        "kind": "prompt",
        "model": FOUNDRY_DEPLOYMENT,
        "instructions": "You are a weather bot. Use fetch_weather to answer weather questions.",
        "tools": [{
            "type": "function",
            "name": weather_tool_definition["name"],
            "description": weather_tool_definition["description"],
            "parameters": weather_tool_definition["parameters"]
        }]
    }
}

print('DEBUG: FOUNDRY_PROJECT_ENDPOINT=', FOUNDRY_PROJECT_ENDPOINT)
print('DEBUG: API KEY present=', AZURE_OPENAI_API_KEY is not None)
print('DEBUG: agent_payload=', json.dumps(agent_payload, indent=2))
resp = requests.post(
    f"{FOUNDRY_PROJECT_ENDPOINT}/agents?api-version=v1",
    headers=foundry_headers,
    json=agent_payload
)
print('DEBUG: status', resp.status_code)
print('DEBUG: response', resp.text)
if resp.status_code == 409:
    # Agent already exists — delete it and recreate
    print(f"Agent '{agent_name}' already exists, deleting and recreating...")
    requests.delete(
        f"{FOUNDRY_PROJECT_ENDPOINT}/agents/{agent_name}?api-version=v1",
        headers=foundry_headers
    ).raise_for_status()
    resp = requests.post(
        f"{FOUNDRY_PROJECT_ENDPOINT}/agents?api-version=v1",
        headers=foundry_headers,
        json=agent_payload
    )
resp.raise_for_status()
foundry_agent = resp.json()
foundry_agent_id = foundry_agent["id"]
print(f"Created Foundry agent: {foundry_agent_id}  (visible in Azure AI Foundry portal)")

# -------------------------------------------------------
# Azure OpenAI Assistants API — for thread/run execution
# -------------------------------------------------------
# The Foundry Agents service does not yet expose a threads/runs API,
# so we use the Azure OpenAI Assistants API for execution.
# We create a matching assistant here that mirrors the Foundry agent.
openai_client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-12-01-preview",
)

assistant = openai_client.beta.assistants.create(
    model=DEPLOYMENT,
    name=agent_name,
    instructions="You are a weather bot. Use fetch_weather to answer weather questions.",
    tools=[{"type": "function", "function": weather_tool_definition}]
)
print(f"Created OpenAI assistant (for execution): {assistant.id}")

# -------------------------------------------------------
# Function registry for manual handling
# -------------------------------------------------------
function_registry = {
    "fetch_weather": fetch_weather
}

# -------------------------------------------------------
# Create thread and send user message
# -------------------------------------------------------
thread = openai_client.beta.threads.create()
print(f"Created thread: {thread.id}")

msg = openai_client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Hello, what's the weather in Brisbane?"
)
print(f"Created message: {msg.id}")

# -------------------------------------------------------
# Run assistant with manual function call handling
# -------------------------------------------------------
run = openai_client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
)

max_iterations = 30
iteration = 0

while run.status in ["queued", "in_progress", "requires_action"] and iteration < max_iterations:
    iteration += 1

    if run.status == "requires_action":
        tool_calls = run.required_action.submit_tool_outputs.tool_calls
        tool_outputs = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            print(f"Calling function: {function_name} with args: {function_args}")

            if function_name in function_registry:
                function_result = function_registry[function_name](**function_args)
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": function_result
                })

        run = openai_client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )
    else:
        time.sleep(1)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )

print(f"Run status: {run.status}")

# -------------------------------------------------------
# Display output
# -------------------------------------------------------
messages = openai_client.beta.threads.messages.list(thread_id=thread.id)
print("\n===== AGENT OUTPUT =====\n")
for m in messages:
    if m.role == "assistant":
        for c in m.content:
            if c.type == "text":
                print(c.text.value)

# -------------------------------------------------------
# Cleanup — uncomment to delete after testing
# -------------------------------------------------------
# openai_client.beta.assistants.delete(assistant.id)
# requests.delete(
#     f"{FOUNDRY_PROJECT_ENDPOINT}/agents/{foundry_agent_id}?api-version=v1",
#     headers=foundry_headers
# )
