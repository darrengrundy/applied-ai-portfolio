import os
import sys
import warnings
from typing import override
from openai import AzureOpenAI, AssistantEventHandler
from dotenv import load_dotenv, find_dotenv

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode characters like ° or — printed below; force UTF-8 stdout.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Environment ────────────────────────────────────────────
load_dotenv(find_dotenv())

AZURE_OPENAI_ENDPOINT = os.getenv(
    "AZURE_OPENAI_ENDPOINT",
    "https://tdai-foundry.cognitiveservices.azure.com/"
)
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
DEPLOYMENT   = os.getenv("DEPLOYMENT_NAME_GPT_4_mini", "gpt-4o-mini")
API_VERSION  = "2024-12-01-preview"
STUDENT_NAME = os.getenv("STUDENT_NAME", "student")

CSV_PATH = os.path.join(os.path.dirname(__file__), "asx_100_quaterly_results.csv")
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

# ── Client ─────────────────────────────────────────────────
client = AzureOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=API_VERSION,
)

# ── 1. Upload CSV ──────────────────────────────────────────
# Filename includes student name so it is identifiable
# under Azure OpenAI Studio > Files.
file_name = f"{STUDENT_NAME}_{os.path.basename(CSV_PATH)}"
print(f"Uploading '{file_name}' ...")
with open(CSV_PATH, "rb") as f:
    uploaded_file = client.files.create(file=(file_name, f), purpose="assistants")
print(f"  File ID : {uploaded_file.id}")


# ── 2. Create assistant with code interpreter ──────────────
assistant = client.beta.assistants.create(
    model=DEPLOYMENT,
    name=f"data-analysis-agent-{STUDENT_NAME}",
    instructions="You are a helpful agent that analyzes financial data from a CSV file and generates insights, charts, and tables based on user requests.",
    tools=[{"type": "code_interpreter"}],
    tool_resources={"code_interpreter": {"file_ids": [uploaded_file.id]}}
)
print(f"Created assistant: {assistant.id} ({assistant.name})")
print("  Visible in Azure OpenAI Studio > Assistants\n")

# ── 3. Create thread and message ───────────────────────────
thread = client.beta.threads.create()

PROMPT = """
You are a data-analysis agent. Analyze the uploaded CSV file
(ASX 100 quarterly results) and do the following:

1. Load the file into a DataFrame. Expected columns:
   name, ASX_Code, sector, industry, revenue, operating_expenses,
   operating_profit, operating_profit_margin, depreciation, interest,
   profit_before_tax, tax, net_profit, EPS, profit_TTM, EPS_TTM.
   Convert any numeric fields stored as strings.

2. Create a bar chart of operating_profit for companies in the
   Financials sector. Label the x-axis with company names.

3. Print a table of the top 10 companies by operating_profit.

4. Finish with a short written summary of the key insights.
"""

client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content=PROMPT
)

# ── 4. Stream the run ──────────────────────────────────────
# Shows code being written and text output in real time.
class EventHandler(AssistantEventHandler):
    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    def on_tool_call_created(self, tool_call):
        print("\n[Code interpreter: writing code...]\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == "code_interpreter" and delta.code_interpreter.input:
            print(delta.code_interpreter.input, end="", flush=True)

print("Running analysis — streaming below:\n" + "─" * 60)

with client.beta.threads.runs.stream(
    thread_id=thread.id,
    assistant_id=assistant.id,
    event_handler=EventHandler(),
) as stream:
    stream.until_done()

print("\n" + "─" * 60)

# ── 5. Download any generated charts ──────────────────────
messages = client.beta.threads.messages.list(thread_id=thread.id)
chart_index = 1
for msg in messages:
    if msg.role == "assistant":
        for item in msg.content:
            if item.type == "image_file":
                img_data = client.files.content(item.image_file.file_id)
                out_path = os.path.join(
                    os.path.dirname(__file__),
                    f"{STUDENT_NAME}_chart_{chart_index}.png"
                )
                with open(out_path, "wb") as f:
                    f.write(img_data.read())
                print(f"\n[Chart saved: {out_path}]")
                chart_index += 1

# ── 6. Clean up uploaded file ──────────────────────────────
# client.files.delete(uploaded_file.id)
# print(f"\nDeleted uploaded file {uploaded_file.id}.")

# Uncomment to also delete the assistant after each run:
# client.beta.assistants.delete(assistant.id)
# print("Deleted assistant.")
