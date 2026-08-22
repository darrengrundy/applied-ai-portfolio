from dotenv import load_dotenv
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

# -------------------------------------------------------
# Demo 1: Business Card Reader — Azure Document Intelligence
#
# Uses the prebuilt-read model to extract all text from a
# business card image using OCR. No configuration needed.
#
# What it shows:
#   - Every line of text detected on the card
#   - Word-level confidence scores
#   - Page dimensions and layout
#
# Key insight: Document Intelligence reads WHAT is on the
# card. Content Understanding (Demo 2) understands WHAT
# each piece of text MEANS.
#
# Usage:
#   python 1_DocIntelligence_BusinessCard.py
# -------------------------------------------------------
load_dotenv()

ENDPOINT   = os.getenv("DOC_INTELLIGENCE_ENDPOINT", "").rstrip("/")
KEY        = os.getenv("DOC_INTELLIGENCE_KEY")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CARDS_DIR  = os.path.join(SCRIPT_DIR, "sample_cards")


def get_client():
    return DocumentIntelligenceClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
    )


def read_card(client, image_path: str):
    """Send a local image to the prebuilt-read model."""
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    poller = client.begin_analyze_document(
        "prebuilt-read",
        body=image_bytes,
        content_type="application/octet-stream",
    )
    return poller.result()


def print_card(result, filename: str):
    print(f"\n{'=' * 50}")
    print(f"  {filename}")
    print(f"{'=' * 50}")

    for page in result.pages:
        print(f"  Page size  : {page.width:.0f} x {page.height:.0f} px")
        print(f"  Lines found: {len(page.lines or [])}")
        print()
        print("  --- Text extracted from card ---")
        for line in (page.lines or []):
            print(f"    {line.content}")
    print()


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 50)
    print("  Business Card Reader")
    print("  Azure Document Intelligence — prebuilt-read")
    print("=" * 50)
    print()
    print("OCR extracts all text from the card — no schema needed.\n")

    client = get_client()

    images = [
        f for f in os.listdir(CARDS_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    ]

    if not images:
        print(f"No images found in {CARDS_DIR}")
        return

    print(f"Found {len(images)} card(s).\n")

    for filename in sorted(images):
        path = os.path.join(CARDS_DIR, filename)
        print(f"Reading: {filename}...", end=" ", flush=True)
        result = read_card(client, path)
        print("done.")
        print_card(result, filename)

    print("Key Concept:")
    print("  prebuilt-read extracts raw text — it sees all the words")
    print("  but doesn't know which one is the name vs the email.")
    print()
    print("  That's where Content Understanding (Demo 2) comes in:")
    print("  you tell it WHAT fields to extract and it reasons about")
    print("  which text belongs to each field.\n")


if __name__ == "__main__":
    main()
