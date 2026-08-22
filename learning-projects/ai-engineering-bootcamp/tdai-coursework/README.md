# TDAI AI Engineering Coursework

This directory is a curated, runnable snapshot of the Python coursework completed during the TDAI AI Engineering Bootcamp. It preserves the weekly source structure used in class while documenting Darren Grundy's own execution and adaptation work.

## Coverage

| Week | Topic | Python files | Validation status |
|---|---|---:|---|
| [1](Week1/) | LLM fundamentals, prompting, embeddings and RAG | 10 | 10/10 run successfully |
| [2](Week2/) | Foundry agents, function tools and code interpreter | 8 | 8/8 accounted for; active demonstrations passed |
| [3](Week3/) | Prompt Flow, tracing and observability | 4 | 4/4 run successfully |
| [4](Week4/) | No class assignment | 0 | Not applicable |
| [5](Week5/) | Semantic Kernel and Azure AI Content Safety | 8 | 8/8 run successfully; notebook also validated in VS Code |
| [6](Week6/) | Azure AI Vision and OCR | 7 | 7/7 accounted for; five passed and two legacy Custom Vision examples are externally constrained |
| [7](Week7/) | Language, speech, translation and GPT audio | 20 | 20/20 accounted for; all active demonstrations passed |
| [8](Week8/) | Document Intelligence, AI Search, MCP and multi-agent workflows | 13 | 13/13 accounted for; all safe runtime demonstrations passed |

**Total: 70 Python files accounted for.** The current upstream course contains 70 rather than 68 Python files. Nothing has been removed merely to force an older file count.

See [Execution status](EXECUTION_STATUS.md) for the validation method, exceptions and noteworthy outputs.

## Run locally

From this directory:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy the relevant template to `.env`, add your own Azure resource details, then run a script from its expected working directory. For example:

```powershell
Copy-Item Week7\Session1\.env.example Week7\Session1\.env
python Week7\Session1\1_LanguageDetection.py
```

Never commit the resulting `.env` file. Many demonstrations call billable Azure services and some setup utilities create or update cloud resources, so read the weekly README and source comments before running them.

## What is intentionally excluded

- credentials and local `.env` files;
- virtual environments, caches and editor settings;
- generated charts, speech files and local test outputs that were not part of the tracked course inputs;
- Prompt Flow UI/session telemetry under `.promptflow`;
- unrelated repositories and local workspace material.

Tracked sample data and media required by the demonstrations are retained. The included `.wav` file is a course input used by a transcription exercise, not a personal recording.

## Attribution

The exercises began from course materials in the private `TDAI-admin/AI-Engineering-TDAI` repository and are published here as completed student coursework at the lecturer's direction. Darren configured the services, executed the demonstrations in VS Code, diagnosed compatibility and platform issues, and adapted selected examples for the current Microsoft Foundry and Azure SDK environment.

See [ATTRIBUTION.md](ATTRIBUTION.md) for the scope of authorship and reuse.
