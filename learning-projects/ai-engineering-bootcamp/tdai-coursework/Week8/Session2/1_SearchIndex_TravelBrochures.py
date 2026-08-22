from dotenv import load_dotenv
import os
import base64
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient

# -------------------------------------------------------
# Demo 1: Knowledge Mining — Margie's Travel Brochures
#
# This script queries an Azure AI Search index that was built
# by an indexer pipeline in the Azure portal. The pipeline:
#
#   1. Reads PDFs from the documents/ folder (uploaded to
#      Azure Blob Storage as the data source)
#   2. Runs cognitive skills to extract:
#         - locations   (Named Entity Recognition)
#         - people      (Named Entity Recognition)
#         - keyphrases  (Key Phrase Extraction)
#   3. Stores the enriched data in the search index
#
# This script is the front-end — it lets you search across
# all that extracted content with a simple text query.
#
# Prerequisites (set up once in the Azure portal):
#   1. Create a Blob Storage container and upload documents/
#   2. Create an AI Search indexer pointing to that container
#      with the cognitive skills above enabled
#   3. Set INDEX_NAME in .env to match your indexer's index
#
# Usage:
#   python 1_SearchIndex_TravelBrochures.py
# -------------------------------------------------------


def main():

    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    try:

        # Get config settings
        load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
        search_endpoint = os.getenv('SEARCH_ENDPOINT')
        query_key = os.getenv('QUERY_KEY')
        index = os.getenv('INDEX_NAME')

        missing = [
            name for name, value in {
                "SEARCH_ENDPOINT": search_endpoint,
                "QUERY_KEY": query_key,
                "INDEX_NAME": index,
            }.items() if not value
        ]
        if missing:
            raise ValueError(
                f"Missing setting(s) in Week8/Session2/.env: {', '.join(missing)}"
            )

        # Get a search client
        search_client = SearchClient(search_endpoint, index, AzureKeyCredential(query_key))

        # Loop until the user types 'quit'
        while True:
            # Get query text
            query_text = input("Enter a query (or type 'quit' to exit): ")
            if query_text.lower() == "quit":
                break
            if len(query_text) == 0:
                print("Please enter a query.")
                continue

            # Clear the console
            os.system('cls' if os.name == 'nt' else 'clear')

            # Search the index
            found_documents = search_client.search(
                search_text=query_text,
                select=["id", "locations", "people", "keyphrases"],
                include_total_count=True
            )

            # Parse the results
            print(f"\nSearch returned {found_documents.get_count()} documents:")
            for document in found_documents:
                # The id is a base64-encoded blob URL — decode to get filename
                try:
                    decoded = base64.b64decode(document["id"]).decode("utf-8")
                    doc_name = decoded.split("/")[-1]
                except Exception:
                    doc_name = document["id"]
                print(f"\nDocument: {doc_name}")
                print(" - Locations:")
                for location in document["locations"]:
                    print(f"   - {location}")
                print(" - People:")
                for person in document["people"]:
                    print(f"   - {person}")
                print(" - Key phrases:")
                for phrase in document["keyphrases"]:
                    print(f"   - {phrase}")

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()
