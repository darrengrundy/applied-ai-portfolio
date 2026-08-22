 # Import namespaces
import os
from pathlib import Path
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.ai.language.conversations import ConversationAnalysisClient

load_dotenv(Path(__file__).parent / ".env")
prediction_endpoint = os.getenv("LANGUAGE_ENDPOINT")
prediction_key = os.getenv("LANGUAGE_KEY")

 # Create a client for the Language service model
client = ConversationAnalysisClient(
    prediction_endpoint, AzureKeyCredential(prediction_key))

 # Call the Language service model to get intent and entities
cls_project = 'Menu'
deployment_slot = 'production'

with client:
     query = "Send an email to Adrian"
     result = client.analyze_conversation(
         task={
             "kind": "Conversation",
             "analysisInput": {
                 "conversationItem": {
                     "participantId": "1",
                     "id": "1",
                     "modality": "text",
                     "language": "en",
                     "text": query
                 },
                 "isLoggingEnabled": False
             },
             "parameters": {
                 "projectName": cls_project,
                 "deploymentName": deployment_slot,
                 "verbose": True
             }
         }
     )

top_intent = result["result"]["prediction"]["topIntent"]
entities = result["result"]["prediction"]["entities"]

print("view top intent:")
print("\ttop intent: {}".format(result["result"]["prediction"]["topIntent"]))
print("\tcategory: {}".format(result["result"]["prediction"]["intents"][0]["category"]))
print("\tconfidence score: {}\n".format(result["result"]["prediction"]["intents"][0]["confidenceScore"]))

print("view entities:")
for entity in entities:
     print("\tcategory: {}".format(entity["category"]))
     print("\ttext: {}".format(entity["text"]))
     print("\tconfidence score: {}".format(entity["confidenceScore"]))

print("query: {}".format(result["result"]["query"]))

 # Apply the appropriate action
if top_intent == 'GetTime':
     location = 'local'
     # Check for entities
     if len(entities) > 0:
         # Check for a location entity
         for entity in entities:
             if 'Location' == entity["category"]:
                 # ML entities are strings, get the first one
                 location = entity["text"]
     # Get the time for the specified location
     print(GetTime(location))

elif top_intent == 'GetDay':
     date_string = date.today().strftime("%m/%d/%Y")
     # Check for entities
     if len(entities) > 0:
         # Check for a Date entity
         for entity in entities:
             if 'Date' == entity["category"]:
                 # Regex entities are strings, get the first one
                 date_string = entity["text"]
     # Get the day for the specified date
     print(GetDay(date_string))

elif top_intent == 'GetDate':
     day = 'today'
     # Check for entities
     if len(entities) > 0:
         # Check for a Weekday entity
         for entity in entities:
             if 'Weekday' == entity["category"]:
             # List entities are lists
                 day = entity["text"]
     # Get the date for the specified day
     print(GetDate(day))

else:
     # Some other intent (for example, "None") was predicted
     print('Try asking me for the time, the day, or the date.')


