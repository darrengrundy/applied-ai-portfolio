import os
import sys
import json
import time
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from openai import AzureOpenAI
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
load_dotenv(find_dotenv())

# Use the openai.azure.com endpoint — this creates classic
# assistants with asst_xxx IDs that appear in the Foundry
# portal as "classic" agents, complete with thread history.
AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_CLASSIC_ENDPOINT",
    "https://tdai-foundry.openai.azure.com"
)
DEPLOYMENT = os.getenv("DEPLOYMENT_NAME_GPT_4", "gpt-4o")
STUDENT_NAME = os.getenv("STUDENT_NAME", "student")

# -------------------------------------------------------
# Client — Entra auth (az login) via DefaultAzureCredential
# No API key needed; uses your logged-in Azure account.
# -------------------------------------------------------
credential = DefaultAzureCredential()
token_provider = get_bearer_token_provider(
    credential, "https://cognitiveservices.azure.com/.default"
)

client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    azure_ad_token_provider=token_provider,
    api_version="2024-12-01-preview",
)

# -------------------------------------------------------
# Create assistant
# -------------------------------------------------------
assistant = client.beta.assistants.create(
    model=DEPLOYMENT,
    name=f"weather-agent-{STUDENT_NAME}-classic",
    instructions="You are a weather bot. Use fetch_weather to answer weather questions.",
    tools=[{"type": "function", "function": weather_tool_definition}]
)
print(f"Created classic assistant: {assistant.id}")
print(f"  Name:  {assistant.name}")
print(f"  Model: {assistant.model}")
print(f"  Tools: {[t.type for t in assistant.tools]}")
print()

# -------------------------------------------------------
# Function registry
# -------------------------------------------------------
function_registry = {
    "fetch_weather": fetch_weather
}

# -------------------------------------------------------
# Create thread and send user message
# -------------------------------------------------------
thread = client.beta.threads.create()
print(f"Created thread: {thread.id}")

msg = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="Hello, what is your name?"
)
print(f"Created message: {msg.id}")
print()

# -------------------------------------------------------
# Run assistant with manual function call handling
# -------------------------------------------------------
run = client.beta.threads.runs.create(
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

        run = client.beta.threads.runs.submit_tool_outputs(
            thread_id=thread.id,
            run_id=run.id,
            tool_outputs=tool_outputs
        )
    else:
        time.sleep(1)
        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )

print(f"Run status: {run.status}")

# -------------------------------------------------------
# Display output
# -------------------------------------------------------
messages = client.beta.threads.messages.list(thread_id=thread.id)
print("\n===== AGENT OUTPUT =====\n")
for m in messages:
    if m.role == "assistant":
        for c in m.content:
            if c.type == "text":
                print(c.text.value)

# -------------------------------------------------------
# Cleanup — uncomment to delete after testing
# -------------------------------------------------------
# client.beta.assistants.delete(assistant.id)
# print("Deleted assistant.")
