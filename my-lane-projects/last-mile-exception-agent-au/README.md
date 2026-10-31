# Last-Mile Exception Agent (Australia)

> Multi-agent handling of last-mile delivery exceptions for an Australian online retailer, shown on one synthetic day of 50,000 parcels across Melbourne and Sydney.

## Project status

**Status:** In progress - synthetic delivery day built; playbook, agent port and demo page not yet built

**Context:** Australian rebuild of [delivery-exception-agent](../delivery-exception-agent/) (UT Austin course project) for My Lane AI

## Problem

TBC

## Setup

```bash
pip install -r requirements.txt
python ref/get_reference.py                 # Australian postcode table
python synthetic/generate.py --out data     # one seeded delivery day (Stoa & Co., Fri 27 Feb 2026)
```

## Attribution

Architecture adapted from my UT Austin Post-Graduate Program in AI Agents for Business Applications final project. The Australian scenario, data and playbook are new and fully synthetic. Postcode coordinates: [matthewproctor/australianpostcodes](https://github.com/matthewproctor/australianpostcodes).

## Licence

No project-specific licence has been granted. Unless stated otherwise, this documentation and the original implementation are all rights reserved.
