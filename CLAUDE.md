# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A public-facing portfolio of applied AI engineering work — course assignments and independent prototypes — not a single application. There is no repo-wide build, test, or lint step; each project under `learning-projects/` or `my-lane-projects/` is a small, independent Python program with its own `requirements.txt` and README. Work currently happens on the `docs/portfolio-foundation` branch (not yet merged to `main`).

## Setup and running a project

Every project follows the same pattern — `cd` into the project folder, then:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
az login
```

Fill in the real values in `.env` (never commit it — see Security below), then run the script(s) under `src/`, e.g. `python src/chat_app.py`.

Authentication is Microsoft Entra ID throughout, not API keys: scripts use `azure.identity.DefaultAzureCredential` (directly with `AIProjectClient`, or via `get_bearer_token_provider(..., "https://ai.azure.com/.default")` when calling the OpenAI SDK against an Azure OpenAI-compatible endpoint). Every script validates required `.env` settings up front with a `require_setting(name)` helper that raises a clear error rather than failing deep in an API call — reuse that helper rather than reading `os.environ` directly when adding a new project.

## Repository structure and conventions

```text
applied-ai-portfolio/
|-- learning-projects/          # course assignments (see ai-engineering-bootcamp/ for the fullest example)
|   |-- ai-engineering-bootcamp/
|   |-- microsoft-ai-engineering/
|   `-- quantic-ai-engineering/
|-- my-lane-projects/           # independent prototypes from My Lane
|-- earlier-projects/           # older work, added only after an attribution/secrets review
|-- docs/architecture/, docs/assets/   # genuinely cross-project diagrams/assets only; project-specific ones stay with the project
`-- templates/PROJECT_README_TEMPLATE.md
```

Each project directory is self-contained: `README.md`, `.env.example`, `requirements.txt`, `src/`. New projects should be scaffolded from `templates/PROJECT_README_TEMPLATE.md`, which defines the required README sections (Problem, Solution, Architecture, Key capabilities, Repository structure, Setup, Testing and evidence, Known limitations, Security and responsible AI, What I learned, Attribution, Licence). Every existing project README follows this shape — match it rather than inventing a different structure.

**Status is tracked honestly, not aspirationally.** Project READMEs use a `**Status:**` line (e.g. "Implementation complete - Azure validation pending", "Plan documented - blocked on model deployment prerequisite") and a "Testing and evidence" section that states plainly what has and hasn't been verified against a live Azure resource. Don't upgrade a project's claimed status without new evidence to back it. `learning-projects/ai-engineering-bootcamp/AZURE_PLATFORM_BLOCKER.md` tracks an ongoing Azure AI Foundry model-deployment issue that currently blocks live validation across most of that folder's projects — check it before assuming a project *should* be runnable end-to-end right now, and update it (with a dated entry) if you re-diagnose the issue rather than replacing the existing history.

## Security and content policy (CONTRIBUTING.md)

- `.env` holds real credentials/endpoints and is git-ignored; only `.env.example` (placeholder values) is committed.
- Before adding screenshots or "publishing" a project, scrub tenant IDs, keys, endpoint URLs, and email addresses, and check **git history**, not just current files, for anything sensitive.
- Course-supplied starter files (grounding documents, brochures, lab data) are referenced by source URL and **not redistributed** in this repo — see existing projects' `.gitignore`-covered local folders (e.g. `brochures/`, `agent_outputs/`) for the pattern.
- Identify copied/adapted starter code and attribute it in the project's "Attribution" section rather than presenting it as original.
- No repository-wide licence has been applied — treat contents as all-rights-reserved unless a specific project states otherwise.
- Commit messages use a `type: summary` convention seen throughout the history — `docs:`, `feat:`, `fix:`, `security:`.
