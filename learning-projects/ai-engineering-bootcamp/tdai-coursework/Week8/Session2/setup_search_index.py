"""
One-time setup: creates the Azure AI Search index and populates it with
enriched travel brochure content.

What this does:
  1. Creates (or recreates) the search index with the right schema
  2. Reads each PDF in documents/ with pypdf
  3. Calls Azure AI Language (via Foundry) for NER and key phrases
  4. Pushes the enriched documents to the index

Run once before using 1_SearchIndex_TravelBrochures.py or 2_SemanticSearch.py.

Requirements:
  pip install azure-search-documents azure-ai-textanalytics pypdf python-dotenv
"""

import os
import json
import re
import time
from dotenv import load_dotenv

import pypdf
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SimpleField,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SemanticConfiguration,
    SemanticSearch,
    SemanticPrioritizedFields,
    SemanticField,
)
from azure.ai.textanalytics import TextAnalyticsClient

load_dotenv()

SEARCH_ENDPOINT = os.getenv("SEARCH_ENDPOINT", "").rstrip("/")
ADMIN_KEY       = os.getenv("ADMIN_KEY")
INDEX_NAME      = os.getenv("INDEX_NAME", "index-tdai-aisearch")
LANGUAGE_KEY    = os.getenv("LANGUAGE_KEY") or os.getenv("AZURE_AI_KEY")
LANGUAGE_ENDPOINT = os.getenv("LANGUAGE_ENDPOINT") or "https://tdai-foundry.cognitiveservices.azure.com/"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR   = os.path.join(SCRIPT_DIR, "documents")


def extract_text_from_pdf(path: str) -> str:
    """Extract all text from a PDF file."""
    reader = pypdf.PdfReader(path)
    parts = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            parts.append(text)
    return " ".join(parts)


def extract_entities_and_phrases(texts: list[str], language_client):
    """Run NER (locations + people) and key phrase extraction on a batch of texts."""
    results = {"locations": [], "people": [], "keyphrases": []}

    # NER
    try:
        ner_results = language_client.recognize_entities(texts)
        for doc in ner_results:
            if not doc.is_error:
                for entity in doc.entities:
                    if entity.category == "Location" and entity.text not in results["locations"]:
                        results["locations"].append(entity.text)
                    elif entity.category == "Person" and entity.text not in results["people"]:
                        results["people"].append(entity.text)
    except Exception as e:
        print(f"    NER warning: {e}")

    # Key phrases
    try:
        kp_results = language_client.extract_key_phrases(texts)
        for doc in kp_results:
            if not doc.is_error:
                for phrase in doc.key_phrases:
                    if phrase not in results["keyphrases"]:
                        results["keyphrases"].append(phrase)
    except Exception as e:
        print(f"    Key phrase warning: {e}")

    return results


def create_index(index_client):
    """Create or replace the search index."""
    fields = [
        SimpleField(name="id",         type=SearchFieldDataType.String, key=True, filterable=True),
        SearchableField(name="content",    type=SearchFieldDataType.String),
        SimpleField(name="source",     type=SearchFieldDataType.String, retrievable=True),
        SearchField(name="locations",  type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True, retrievable=True),
        SearchField(name="people",     type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True, retrievable=True),
        SearchField(name="keyphrases", type=SearchFieldDataType.Collection(SearchFieldDataType.String), searchable=True, retrievable=True),
    ]

    semantic_config = SemanticConfiguration(
        name="default",
        prioritized_fields=SemanticPrioritizedFields(
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[SemanticField(field_name="keyphrases")],
        ),
    )
    semantic_search = SemanticSearch(configurations=[semantic_config])

    index = SearchIndex(name=INDEX_NAME, fields=fields, semantic_search=semantic_search)

    try:
        index_client.delete_index(INDEX_NAME)
        print(f"  Deleted existing index '{INDEX_NAME}'.")
    except Exception:
        pass

    index_client.create_index(index)
    print(f"  Created index '{INDEX_NAME}'.")


def main():
    print("=" * 55)
    print("  Search Index Setup — Margie's Travel Brochures")
    print("=" * 55)
    print()

    # Clients
    index_client    = SearchIndexClient(SEARCH_ENDPOINT, AzureKeyCredential(ADMIN_KEY))
    search_client   = SearchClient(SEARCH_ENDPOINT, INDEX_NAME, AzureKeyCredential(ADMIN_KEY))
    language_client = TextAnalyticsClient(LANGUAGE_ENDPOINT, AzureKeyCredential(LANGUAGE_KEY))

    # Step 1: Create index
    print("Step 1 — Creating index...")
    create_index(index_client)
    print()

    # Step 2: Process each PDF
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"No PDFs found in {DOCS_DIR}")
        return

    print(f"Step 2 — Processing {len(pdf_files)} documents...")
    documents = []

    for filename in sorted(pdf_files):
        path = os.path.join(DOCS_DIR, filename)
        print(f"  {filename}...")

        # Extract text
        text = extract_text_from_pdf(path)
        # Truncate to 5000 chars to stay within Language API limits per document
        text_chunk = text[:5000]

        # Run Language enrichment
        enrichment = extract_entities_and_phrases([text_chunk], language_client)

        doc_id = re.sub(r"[^a-zA-Z0-9_-]", "_", os.path.splitext(filename)[0])
        documents.append({
            "id": doc_id,
            "content": text[:10000],
            "source": filename,
            "locations":  enrichment["locations"][:50],
            "people":     enrichment["people"][:50],
            "keyphrases": enrichment["keyphrases"][:50],
        })

        print(f"    Locations: {len(enrichment['locations'])}, "
              f"People: {len(enrichment['people'])}, "
              f"Key phrases: {len(enrichment['keyphrases'])}")

    print()

    # Step 3: Upload to index
    print("Step 3 — Uploading documents to index...")
    results = search_client.upload_documents(documents=documents)
    succeeded = sum(1 for r in results if r.succeeded)
    print(f"  Uploaded {succeeded}/{len(documents)} documents.")
    print()

    print("Setup complete! You can now run:")
    print("  python 1_SearchIndex_TravelBrochures.py")
    print("  python 2_SemanticSearch.py")


if __name__ == "__main__":
    main()
