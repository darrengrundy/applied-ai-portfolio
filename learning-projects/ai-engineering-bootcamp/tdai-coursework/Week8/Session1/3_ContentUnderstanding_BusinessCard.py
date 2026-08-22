from dotenv import load_dotenv
import os
import json
from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.core.credentials import AzureKeyCredential
import mimetypes
from azure.core.exceptions import AzureError

# -------------------------------------------------------
# Demo 3: Business Card Analyser — Azure AI Content Understanding
#
# Unlike Document Intelligence (Demos 1 & 2), Content
# Understanding lets YOU define exactly which fields to
# extract via a custom JSON schema created in the Studio.
#
# The model reasons from context — no retraining needed.
# To add a field, update the analyzer schema in the Studio.
#
# What it does:
#   1. Connects to a pre-built analyzer (created in Content Understanding Studio)
#   2. Reads each image in sample_cards/
#   3. Extracts the schema fields and prints them
#   4. Saves the full raw result to results_<filename>.json
#
# Requirements:
#   pip install azure-ai-contentunderstanding python-dotenv
#
# .env values needed:
#   CONTENT_UNDERSTANDING_ENDPOINT
#   CONTENT_UNDERSTANDING_KEY
#   ANALYZER_NAME
#
# Usage:
#   python 3_ContentUnderstanding_BusinessCard.py
# -------------------------------------------------------
load_dotenv()

ENDPOINT      = os.getenv("CONTENT_UNDERSTANDING_ENDPOINT", "").rstrip("/")
KEY           = os.getenv("CONTENT_UNDERSTANDING_KEY")
ANALYZER_NAME = os.getenv("ANALYZER_NAME", "businesscardanalyser")
API_VERSION   = os.getenv("CONTENT_UNDERSTANDING_API_VERSION", "2025-05-01-preview")
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR     = os.path.join(SCRIPT_DIR, "sample_cards")


def get_client():
    return ContentUnderstandingClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        api_version=API_VERSION,
    )


def analyze_card(client, image_path: str):
    """
    Submit a local image for analysis.
    Reads the file as bytes and sends it directly to the analyzer.
    """
    with open(image_path, "rb") as f:
        image_data = f.read()

    mime_type, _ = mimetypes.guess_type(image_path)
    mime_type = mime_type or "image/jpeg"

    poller = client.begin_analyze(
        analyzer_id=ANALYZER_NAME,
        body=image_data,
        content_type=mime_type,
    )
    return poller.result()


def print_result(result, filename: str):
    print(f"{'=' * 45}")
    print(f"  {filename}")
    print(f"{'=' * 45}")

    result_dict = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    contents = result_dict.get("contents") or result_dict.get("result", {}).get("contents", [])

    if not contents:
        print("  No content returned.")
        print()
        return

    for content in contents:
        fields = content.get("fields", {})
        if not fields:
            continue
        for field_name, field_data in fields.items():
            value = field_data.get("valueString") or field_data.get("value") or "-"
            print(f"  {field_name:<10}: {value}")

    print()


def save_results(result, filename: str):
    """Save the full raw JSON result to a file for inspection."""
    result_dict = result.as_dict() if hasattr(result, "as_dict") else dict(result)
    output_path = os.path.join(SCRIPT_DIR, f"results_{os.path.splitext(filename)[0]}.json")
    with open(output_path, "w") as f:
        json.dump(result_dict, f, indent=4, default=str)
    print(f"  Full result saved to: {os.path.basename(output_path)}")


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 45)
    print("  Business Card Analyser")
    print("  Azure AI Content Understanding")
    print("=" * 45)
    print()
    print(f"  Analyzer : {ANALYZER_NAME}")
    print(f"  Endpoint : {ENDPOINT}")
    print()

    client = get_client()

    images = [
        f for f in os.listdir(CARDS_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not images:
        print(f"No images found in {CARDS_DIR}")
        return

    print(f"Found {len(images)} card(s) to analyse.\n")

    for filename in sorted(images):
        path = os.path.join(CARDS_DIR, filename)
        print(f"Analysing: {filename}...", end=" ", flush=True)
        try:
            result = analyze_card(client, path)
            print("done.")
            print_result(result, filename)
            save_results(result, filename)
        except AzureError as err:
            print(f"failed.\n  [Azure Error]: {err.message}\n")
        except Exception as ex:
            print(f"failed.\n  [Error]: {ex}\n")

    print("Key Concept:")
    print("  The fields extracted are defined entirely in")
    print("  the analyzer schema set up in Content Understanding Studio.")
    print("  Add or remove fields in the Studio and run again.")
    print()


if __name__ == "__main__":
    main()
