from dotenv import load_dotenv
import os
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature
from azure.core.credentials import AzureKeyCredential

# -------------------------------------------------------
# Demo 2: Business Card Analyser — Structured Extraction
#         Azure Document Intelligence (prebuilt-layout)
#
# Takes the next step beyond raw OCR (Demo 1):
# the layout model detects KEY–VALUE PAIRS on the card.
# Instead of just reading text, it understands the
# relationship between labels and their values.
#
# Key difference from Demo 1:
#   Demo 1 → lines of text (all equal, no structure)
#   Demo 2 → key: value pairs (name <-> Dr. Avery Smith)
#
# Key difference from Content Understanding:
#   Layout KV pairs = detected from document layout
#   Content Understanding = YOU define what fields to extract
#
# Usage:
#   python 2_DocIntelligence_Layout.py
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


def analyse_card(client, image_path: str):
    """
    Use prebuilt-layout with key-value pair detection.
    The model finds label:value relationships on the card.
    """
    with open(image_path, "rb") as f:
        image_bytes = f.read()

    poller = client.begin_analyze_document(
        "prebuilt-layout",
        body=image_bytes,
        content_type="application/octet-stream",
        features=[DocumentAnalysisFeature.KEY_VALUE_PAIRS],
    )
    return poller.result()


def print_card(result, filename: str):
    print(f"\n{'=' * 55}")
    print(f"  {filename}")
    print(f"{'=' * 55}")

    kv_pairs = result.key_value_pairs or []

    if not kv_pairs:
        print("  No key-value pairs detected.")
        print()
        return

    print(f"  Key-value pairs found: {len(kv_pairs)}")
    print()
    print("  {:<20} {}".format("KEY", "VALUE"))
    print("  " + "-" * 50)

    for pair in kv_pairs:
        key   = pair.key.content.strip()   if pair.key   else "—"
        value = pair.value.content.strip() if pair.value else "—"
        confidence = pair.confidence or 0
        print(f"  {key:<20} {value}  (confidence: {confidence:.0%})")

    print()


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 55)
    print("  Business Card Analyser — Structured Extraction")
    print("  Azure Document Intelligence — prebuilt-layout")
    print("=" * 55)
    print()
    print("Layout model detects key-value relationships on the card.\n")

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
        print(f"Analysing: {filename}...", end=" ", flush=True)
        result = analyse_card(client, path)
        print("done.")
        print_card(result, filename)

    print("Key Concepts:")
    print()
    print("  Demo 1 (prebuilt-read)   -> extracts all text lines")
    print("  Demo 2 (prebuilt-layout) -> detects key:value structure")
    print()
    print("  Content Understanding takes this further:")
    print("  YOU define the schema -- tell the model exactly which")
    print("  fields to extract (Name, Company, Phone...) and it")
    print("  reasons about which text on the card fills each field.")
    print("  No training required -- just update the JSON schema.\n")


if __name__ == "__main__":
    main()
