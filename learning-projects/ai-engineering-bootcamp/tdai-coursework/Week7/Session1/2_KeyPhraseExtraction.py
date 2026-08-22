# Azure Language Service - Key Phrase Extraction
# https://learn.microsoft.com/en-GB/azure/ai-services/language-service/
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

def key_phrase_extraction_example(client):

    try:
        documents = ["Key phrase extraction is one of the features offered by Azure AI Language, a collection of machine learning and AI algorithms in the cloud for developing intelligent applications that involve written language."]

        response = client.extract_key_phrases(documents = documents)[0]

        if not response.is_error:
            print("\tKey Phrases:")
            for phrase in response.key_phrases:
                print("\t\t", phrase)
        else:
            print(response.id, response.error)

    except Exception as err:
        print("Encountered exception. {}".format(err))
        
key_phrase_extraction_example(client)