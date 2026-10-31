# Last-Mile Exception Agent (Australia)

> Multi-agent handling of last-mile delivery exceptions for an Australian online retailer, shown on one synthetic day of 50,000 parcels across Melbourne and Sydney.

## Project status

**Status:** In progress - synthetic day, playbook and agent pipeline built; dry-run tested, live Claude run pending; demo page not yet built

**Context:** Australian rebuild of [delivery-exception-agent](../delivery-exception-agent/) (UT Austin course project) for My Lane AI

## Problem

TBC

## Setup

Clone the repo outside OneDrive (git and OneDrive sync clash), then from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python ref/get_reference.py                 # Australian postcode table
python synthetic/generate.py --out data     # one seeded delivery day (Stoa & Co., Fri 27 Feb 2026), ~2 min
```

Your Anthropic key goes in a `.env` file containing one line, `ANTHROPIC_API_KEY=...`. It can live anywhere outside the repo; pass its path with `--env`.

```powershell
python src/run.py --dry-run --sample 5 --out runs/dry                       # plumbing check, no API calls
python src/run.py --env "C:\path\to\.env" --sample 20 --out runs/test20   # ~20 exceptions across every type
python src/evaluate.py --run runs/test20
python src/run.py --env "C:\path\to\.env" --all --wismo -1 --workers 6 --out runs/full   # whole day, resumable
```

## Attribution

Architecture adapted from my UT Austin Post-Graduate Program in AI Agents for Business Applications final project. The Australian scenario, data and playbook are new and fully synthetic. Postcode coordinates: [matthewproctor/australianpostcodes](https://github.com/matthewproctor/australianpostcodes).

## Licence

No project-specific licence has been granted. Unless stated otherwise, this documentation and the original implementation are all rights reserved.
