import os
from pathlib import Path
from dotenv import load_dotenv
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

load_dotenv(Path(__file__).parent / ".env")
endpoint = os.getenv("LANGUAGE_ENDPOINT")
key = os.getenv("LANGUAGE_KEY")

# Authenticate the client using your key and endpoint 
def authenticate_client():
    ta_credential = AzureKeyCredential(key)
    text_analytics_client = TextAnalyticsClient(
            endpoint=endpoint, 
            credential=ta_credential)
    return text_analytics_client

client = authenticate_client()

# Example method for detecting the language of text
def language_detection_example(client):
    try:
        documents = ["Me encanta aprender sobre inteligencia artificial."]
        response = client.detect_language(documents = documents, country_hint = 'us')[0]
        print("Language: ", response.primary_language.name)

    except Exception as err:
        print("Encountered exception. {}".format(err))
language_detection_example(client)