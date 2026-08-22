# Week 2 – Azure AI Agents

This week covers building agents using **Azure AI Foundry**. You will run three demos:

| Demo | Script | What it does |
|---|---|---|
| Function Agent (New Foundry) | `Function_agent/createAgent.py` | Creates an agent via the Foundry Project API — visible in the new Azure AI Foundry portal |
| Function Agent (Classic) | `Function_agent/createAgent_classic.py` | Creates a classic assistant via Entra auth — visible in the Foundry portal as a classic agent with thread history |
| Code Interpreter Agent (Classic) | `codeinterpreter_agent/data_analysis_demo.py` | Uploads a CSV and uses code interpreter to generate charts and analysis — uses API key auth via `openai` SDK |
| Code Interpreter Agent (New Foundry) | `codeinterpreter_agent/data_analysis_demo_new_foundry.py` | Same analysis using the `azure-ai-agents` SDK with Entra auth — agent visible in new AI Foundry portal |

---

## Prerequisites

- Python 3.11 or later
- [VS Code](https://code.visualstudio.com/) with the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python) installed
- [Azure CLI](https://aka.ms/installazurecli) installed and logged in (required for the classic agent script)
- Access to the course Azure subscription (your trainer will provide credentials)

---

## 1. Open the project in VS Code

1. Open VS Code
2. Click **File → Open Folder**
3. Navigate to and select the `AI-Engineering-TDAI` root folder
4. Click **Select Folder**

---

## 2. Open a terminal in VS Code

1. In the menu bar, click **Terminal → New Terminal**
   - A terminal panel will open at the bottom of the screen

> **Tip:** Use the keyboard shortcut **Ctrl + `** (backtick) to toggle the terminal.

---

## 3. Set up your Python environment

If the course virtual environment is not already activated, run:

```bash
# Windows
.venv\Scripts\activate

# Mac / Linux
source .venv/bin/activate
```

You should see `(.venv)` appear at the start of your terminal prompt.

If the `.venv` folder does not exist yet, create it first:

```bash
python -m venv .venv
```

Then activate it (see above) and install dependencies:

```bash
pip install -r requirements.txt
```

---

## 4. Configure your environment variables

Both exercises share a **single `.env` file** located at:

```
Week2/Agents_Demo_code/.env
```

1. Navigate to `Week2/Agents_Demo_code/` in the VS Code Explorer
2. Copy `.env.example` and rename the copy to `.env`

   Or from the terminal:
   ```bash
   cp Week2/Agents_Demo_code/.env.example Week2/Agents_Demo_code/.env
   ```

3. Open `.env` and fill in the values your trainer provides:

```
AZURE_OPENAI_ENDPOINT=https://<your-foundry-resource>.cognitiveservices.azure.com/
AZURE_OPENAI_API_KEY=<provided by trainer>
DEPLOYMENT_NAME_GPT_4_mini=gpt-4o-mini
DEPLOYMENT_NAME_GPT_4=gpt-4o
STUDENT_NAME=your-name
FOUNDRY_PROJECT_ENDPOINT=https://<your-foundry-resource>.services.ai.azure.com/api/projects/<your-project-name>
AZURE_OPENAI_CLASSIC_ENDPOINT=https://<your-foundry-resource>.openai.azure.com
```

> Both scripts in `Function_agent/` and `data_analysis_demo.py` automatically find this file by searching up from their own folder — no need to copy it anywhere else.

---

## 5. Authenticate with Azure

The classic agent script (`createAgent_classic.py`) uses `DefaultAzureCredential`, which reads your `az login` session. Run this once per session:

```bash
az login
```

A browser window will open — sign in with your course Azure account.

> The other scripts (`createAgent.py` and `data_analysis_demo.py`) use an API key from `.env` and do not require `az login`.

---

## 6. Run the demos

### Demo 1 — Function Agent: New Foundry Portal

Creates an agent visible in the **new Azure AI Foundry portal** (`ai.azure.com`).

```bash
cd Week2/Agents_Demo_code/Function_agent
python createAgent.py
```

**What to expect:**
- Agent is created and appears in the Azure AI Foundry portal under **Agents**
- The agent calls `fetch_weather("Melbourne")` to answer the weather question
- Thread execution happens via the Azure OpenAI Assistants API

**Example output:**
```
Created Foundry agent: weather-agent-teaching  (visible in Azure AI Foundry portal)
Created OpenAI assistant (for execution): asst_xxxxxxxxxxxx
Created thread: thread_xxxxxxxxxxxx
Calling function: fetch_weather with args: {'location': 'Melbourne'}
Run status: completed

===== AGENT OUTPUT =====
The weather in Melbourne is windy with a temperature of 17°C.
```

---

### Demo 2 — Function Agent: Classic (with thread history)

Creates a **classic assistant** via Entra auth. Appears in the Foundry portal as a classic agent with full thread history visible.

> Requires `az login` (see Step 5).

```bash
cd Week2/Agents_Demo_code/Function_agent
python createAgent_classic.py
```

**What to expect:**
- A classic `asst_xxx` assistant is created using your Azure login credentials
- The agent calls `fetch_weather("Melbourne")` and responds
- The assistant and its thread are visible in the Azure AI Foundry portal

**Example output:**
```
Created classic assistant: asst_xxxxxxxxxxxx
  Name:  weather-agent-teaching-classic
  Model: gpt-4o
  Tools: ['function']

Created thread: thread_xxxxxxxxxxxx
Calling function: fetch_weather with args: {'location': 'Melbourne'}
Run status: completed

===== AGENT OUTPUT =====
The weather in Melbourne is currently windy, with a temperature of 17°C.
```

---

### Demo 3 — Code Interpreter Agent: Classic (CSV Data Analysis)

```bash
cd Week2/Agents_Demo_code/codeinterpreter_agent
python data_analysis_demo.py
```

> **Note:** Run from the `codeinterpreter_agent/` folder so the CSV file path resolves correctly.

**What to expect:**
- The CSV file (`asx_100_quaterly_results.csv`) is uploaded to the agent
- The agent uses code interpreter to analyse the data and generate a chart
- A top-10 table is printed in the terminal
- Chart is saved as `<STUDENT_NAME>_chart_1.png` in the same folder

**Example output:**
```
Uploading 'teaching_asx_100_quaterly_results.csv' ...
  File ID : assistant-xxxxxxxxxxxx
Created assistant: asst_xxxxxxxxxxxx (data-analysis-agent-teaching)

Running analysis — streaming below:
────────────────────────────────────────────────────────────
[Code interpreter: writing code...]
...
[Chart saved: .../teaching_chart_1.png]
```

---

### Demo 4 — Code Interpreter Agent: New Foundry

Uses the `azure-ai-agents` SDK with Entra auth. The agent appears in the **new Azure AI Foundry portal** under **Agents**.

> Requires `az login` (see Step 5).

```bash
cd Week2/Agents_Demo_code/codeinterpreter_agent
python data_analysis_demo_new_foundry.py
```

**What to expect:**
- Agent is created and visible in the Azure AI Foundry portal under **Agents**
- Same CSV analysis and chart generation as the classic demo
- Chart is saved as `<STUDENT_NAME>_foundry_chart_1.png` in the same folder

**Example output:**
```
Uploading 'teaching_asx_100_quaterly_results.csv' ...
  File ID : assistant-xxxxxxxxxxxx
Created agent: asst_xxxxxxxxxxxx (data-analysis-agent-teaching-foundry)
  Visible in Azure AI Foundry portal > Agents

Running analysis...
────────────────────────────────────────────────────────────
Run status: RunStatus.COMPLETED
────────────────────────────────────────────────────────────
... (top 10 table and summary) ...

[Chart saved: .../teaching_foundry_chart_1.png]
```

**Key differences from the classic demo:**

| | Classic (`data_analysis_demo.py`) | New Foundry (`data_analysis_demo_new_foundry.py`) |
|---|---|---|
| SDK | `openai` (AzureOpenAI) | `azure-ai-agents` (AgentsClient) |
| Auth | API key | Entra (`az login`) |
| Streaming | Yes (real-time code output) | No (blocking `create_and_process`) |
| Portal visibility | Classic Assistants | New AI Foundry Agents |
| Chart filename | `*_chart_1.png` | `*_foundry_chart_1.png` |

---

## Troubleshooting

**`ModuleNotFoundError`**
You are not in the virtual environment, or dependencies are not installed. Run:
```bash
.venv\Scripts\activate     # Windows
pip install -r requirements.txt
```

**`.env` values not loading**
Make sure `.env` exists at `Week2/Agents_Demo_code/.env` (not inside a subfolder). The scripts search upward from their location to find it.

**`FileNotFoundError: CSV file not found`**
Run `data_analysis_demo.py` from the `codeinterpreter_agent/` folder, not from the project root.

**`DefaultAzureCredential failed`** (classic script and new Foundry scripts)
Run `az login` in the terminal before running `createAgent_classic.py` or `data_analysis_demo_new_foundry.py`.

**`Run failed: Rate limit is exceeded`**
The Azure resource has hit its token quota. Wait a minute and try again, or ask your trainer to check the quota.
