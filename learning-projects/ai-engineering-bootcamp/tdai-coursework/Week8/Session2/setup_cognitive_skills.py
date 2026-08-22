"""
One-time setup: adds cognitive skills to the existing indexer pipeline.

What this does:
  1. Creates a skillset (NER → locations & people, KeyPhrase → keyphrases)
  2. Adds the three output fields to the index schema
  3. Updates the indexer to use the skillset + output field mappings
  4. Resets and reruns the indexer so all 6 documents are re-processed

Run once, then run 1_SearchIndex_TravelBrochures.py normally.
"""

import os
import json
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────
SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT", "").rstrip("/")
ADMIN_KEY       = os.getenv("ADMIN_KEY")
INDEX_NAME      = os.getenv("INDEX_NAME")
INDEXER_NAME    = os.getenv("INDEXER_NAME")
SKILLSET_NAME   = os.getenv("SKILLSET_NAME", "skillset")

API = "2024-07-01"
HEADERS = {"Content-Type": "application/json", "api-key": ADMIN_KEY}


def call(method, path, body=None):
    url = f"{SEARCH_ENDPOINT}/{path}?api-version={API}"
    resp = requests.request(method, url, headers=HEADERS,
                            json=body, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"{method} {path} → {resp.status_code}: {resp.text}")
    return resp.json() if resp.text else {}


# ── Step 1: Create skillset ───────────────────────────────────────
print("Step 1 — Creating skillset...")

skillset = {
    "name": SKILLSET_NAME,
    "description": "NER (locations, people) + Key Phrase Extraction",
    "skills": [
        {
            "@odata.type": "#Microsoft.Skills.Text.V3.EntityRecognitionSkill",
            "name": "entity-recognition",
            "categories": ["Location", "Person"],
            "defaultLanguageCode": "en",
            "inputs":  [{"name": "text", "source": "/document/content"}],
            "outputs": [
                {"name": "locations", "targetName": "locations"},
                {"name": "persons",   "targetName": "people"},
            ],
        },
        {
            "@odata.type": "#Microsoft.Skills.Text.KeyPhraseExtractionSkill",
            "name": "key-phrase-extraction",
            "defaultLanguageCode": "en",
            "inputs":  [{"name": "text", "source": "/document/content"}],
            "outputs": [{"name": "keyPhrases", "targetName": "keyphrases"}],
        },
    ],
    # No cognitiveServices key needed for ≤ 20 docs (free tier)
}

call("PUT", f"skillsets/{SKILLSET_NAME}", skillset)
print(f"  Skillset '{SKILLSET_NAME}' created.")


# ── Step 2: Add output fields to the index ───────────────────────
print("Step 2 — Adding fields to the index...")

# Fetch current index definition
index_def = call("GET", f"indexes/{INDEX_NAME}")

existing_names = {f["name"] for f in index_def.get("fields", [])}
new_fields = [
    {"name": "locations",  "type": "Collection(Edm.String)", "searchable": True,  "filterable": False, "retrievable": True},
    {"name": "people",     "type": "Collection(Edm.String)", "searchable": True,  "filterable": False, "retrievable": True},
    {"name": "keyphrases", "type": "Collection(Edm.String)", "searchable": True,  "filterable": False, "retrievable": True},
]

added = []
for field in new_fields:
    if field["name"] not in existing_names:
        index_def["fields"].append(field)
        added.append(field["name"])

if added:
    call("PUT", f"indexes/{INDEX_NAME}", index_def)
    print(f"  Added fields: {', '.join(added)}")
else:
    print("  Fields already exist — no changes needed.")


# ── Step 3: Update indexer to use skillset + output field mappings ─
print("Step 3 — Updating indexer...")

indexer_def = call("GET", f"indexers/{INDEXER_NAME}")

indexer_def["skillsetName"] = SKILLSET_NAME

# Output field mappings: skill output → index field
output_mappings = [
    {"sourceFieldName": "/document/locations",  "targetFieldName": "locations"},
    {"sourceFieldName": "/document/people",      "targetFieldName": "people"},
    {"sourceFieldName": "/document/keyphrases",  "targetFieldName": "keyphrases"},
]

existing_targets = {m["targetFieldName"] for m in indexer_def.get("outputFieldMappings", [])}
for mapping in output_mappings:
    if mapping["targetFieldName"] not in existing_targets:
        indexer_def.setdefault("outputFieldMappings", []).append(mapping)

call("PUT", f"indexers/{INDEXER_NAME}", indexer_def)
print(f"  Indexer '{INDEXER_NAME}' updated with skillset.")


# ── Step 4: Reset + rerun the indexer ────────────────────────────
print("Step 4 — Resetting and rerunning the indexer...")

call("POST", f"indexers/{INDEXER_NAME}/reset")
time.sleep(2)
call("POST", f"indexers/{INDEXER_NAME}/run")
print("  Indexer is running. This takes about 1-2 minutes...")
print()
print("  Monitor progress in Azure Portal:")
print("  AI Search → indexer-tdai → Execution history")
print()
print("Done! Once the indexer finishes, run:")
print("  python 1_SearchIndex_TravelBrochures.py")
