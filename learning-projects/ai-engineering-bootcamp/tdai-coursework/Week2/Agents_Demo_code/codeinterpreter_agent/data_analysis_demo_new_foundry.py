import os
import sys
from azure.ai.agents import AgentsClient
from azure.ai.agents.models import CodeInterpreterTool, FilePurpose, MessageRole, MessageAttachment
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv, find_dotenv

# Windows consoles default to a legacy codepage (e.g. cp1252) that can't
# encode characters like ° or — printed below; force UTF-8 stdout.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# ── Environment ────────────────────────────────────────────
load_dotenv(find_dotenv())

FOUNDRY_PROJECT_ENDPOINT = os.getenv(
    "FOUNDRY_PROJECT_ENDPOINT",
    "https://tdai-foundry.services.ai.azure.com/api/projects/tdai-foundry-project"
)
DEPLOYMENT   = os.getenv("DEPLOYMENT_NAME_FOUNDRY", "gpt-5.2")
STUDENT_NAME = os.getenv("STUDENT_NAME", "student")

CSV_PATH = os.path.join(os.path.dirname(__file__), "asx_100_quaterly_results.csv")
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError(f"CSV not found: {CSV_PATH}")

# ── Client (Entra auth — uses az login session) ────────────
client = AgentsClient(
    endpoint=FOUNDRY_PROJECT_ENDPOINT,
    credential=DefaultAzureCredential()
)

# ── 1. Upload CSV ──────────────────────────────────────────
file_name = f"{STUDENT_NAME}_{os.path.basename(CSV_PATH)}"
print(f"Uploading '{file_name}' ...")
with open(CSV_PATH, "rb") as f:
    uploaded_file = client.files.upload_and_poll(
        file=(file_name, f),
        purpose=FilePurpose.AGENTS
    )
print(f"  File ID : {uploaded_file.id}")

# ── 2. Create agent with code interpreter ──────────────────
code_interpreter = CodeInterpreterTool(file_ids=[uploaded_file.id])

agent = client.create_agent(
    model=DEPLOYMENT,
    name=f"data-analysis-agent-{STUDENT_NAME}-foundry",
    instructions="You are a helpful agent that analyzes financial data from a CSV file and generates insights, charts, and tables based on user requests.",
    tools=code_interpreter.definitions,
    tool_resources=code_interpreter.resources,
)
print(f"Created agent: {agent.id} ({agent.name})")
print("  Visible in Azure AI Foundry portal > Agents\n")

# ── 3. Create thread and message ───────────────────────────
thread = client.threads.create()

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

client.messages.create(
    thread_id=thread.id,
    role="user",
    content=PROMPT,
    attachments=[
        MessageAttachment(file_id=uploaded_file.id, tools=[{"type": "code_interpreter"}])
    ],
)

# ── 4. Run (blocking — handles all tool calls internally) ──
print("Running analysis...\n" + "─" * 60)
run = client.runs.create_and_process(
    thread_id=thread.id,
    agent_id=agent.id
)
print(f"Run status: {run.status}")
print("─" * 60)

# ── 5. Print text output ────────────────────────────────────
messages = client.messages.list(thread_id=thread.id)
print()
for msg in messages:
    if msg.role == MessageRole.AGENT:
        for item in msg.content:
            if item.type == "text":
                print(item.text.value)
            elif item.type == "image_file":
                # Some models attach generated images directly to the
                # message; handled here for completeness.
                file_id = item.image_file.file_id
                img_bytes = b"".join(client.files.get_content(file_id))
                out_path = os.path.join(
                    os.path.dirname(__file__),
                    f"{STUDENT_NAME}_foundry_chart_{file_id}.png"
                )
                with open(out_path, "wb") as f:
                    f.write(img_bytes)
                print(f"\n[Chart saved: {out_path}]")

# ── 6. Download charts ──────────────────────────────────────
# This model/SDK combo uploads generated charts as standalone files
# (purpose "assistants_output") instead of attaching them to the
# message content, so we fetch them separately by run window.
chart_index = 1
for f in client.files.list().data:
    if f.purpose == "assistants_output" and f.created_at >= run.created_at:
        img_bytes = b"".join(client.files.get_content(f.id))
        out_path = os.path.join(
            os.path.dirname(__file__),
            f"{STUDENT_NAME}_foundry_chart_{chart_index}.png"
        )
        with open(out_path, "wb") as out_f:
            out_f.write(img_bytes)
        print(f"\n[Chart saved: {out_path}]")
        chart_index += 1

# ── 7. Clean up ────────────────────────────────────────────
# client.files.delete(uploaded_file.id)
# client.delete_agent(agent.id)
