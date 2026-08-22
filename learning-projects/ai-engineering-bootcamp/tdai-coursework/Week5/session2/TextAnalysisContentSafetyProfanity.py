# Azure AI Content Safety - Modern replacement for Content Moderator
# https://learn.microsoft.com/en-us/azure/ai-services/content-safety/

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from pprint import pprint
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.core.credentials import AzureKeyCredential

load_dotenv()
CONTENT_SAFETY_KEY = os.getenv("AZURE_CONTENT_SAFETY_KEY")
CONTENT_SAFETY_ENDPOINT = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")

# Initialize the client
client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT,
    credential=AzureKeyCredential(CONTENT_SAFETY_KEY)
)

script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "sample.txt")

# Load text from file
with open(file_path, "r", encoding="utf-8") as f:
    text_content = f.read()


# Analyze the text for harmful content
request = AnalyzeTextOptions(
    text=text_content,
    categories=[
        TextCategory.HATE,
        TextCategory.SEXUAL,
        TextCategory.SELF_HARM,
        TextCategory.VIOLENCE
    ],
    output_type="FourSeverityLevels"  # Returns severity 0-6
)

try:
    response = client.analyze_text(request)
    print("=== Content Safety Analysis ===\n")
    
    # Display results for each category
    for category_result in response.categories_analysis:
        print(f"Category: {category_result.category}")
        print(f"Severity: {category_result.severity} (0=Safe, 6=High)")
        print()
    
    # Overall decision
    print("=== Overall Assessment ===")
    if all(cat.severity == 0 for cat in response.categories_analysis):
        print("✓ Content appears safe")
    else:
        print("⚠ Potentially harmful content detected")
        flagged = [cat for cat in response.categories_analysis if cat.severity > 0]
        for cat in flagged:
            print(f"  - {cat.category}: Severity {cat.severity}")
    
    print("\n=== Full Response ===")
    pprint(response.as_dict())
    
except Exception as e:
    print(f"Error analyzing content: {e}")