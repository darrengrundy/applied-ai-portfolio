# Combined Azure AI Content Safety + PII Detection
# Replaces deprecated Azure Content Moderator
# https://learn.microsoft.com/en-us/azure/ai-services/content-safety/
# https://learn.microsoft.com/en-us/azure/ai-services/language-service/personally-identifiable-information/

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from pprint import pprint
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeTextOptions, TextCategory
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()
CONTENT_SAFETY_KEY = os.getenv("AZURE_CONTENT_SAFETY_KEY")
CONTENT_SAFETY_ENDPOINT = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")

# Azure AI Language credentials (for PII detection)
LANGUAGE_ENDPOINT = os.getenv("AZURE_LANGUAGE_ENDPOINT")
LANGUAGE_KEY = os.getenv("AZURE_LANGUAGE_KEY")
# ============================================================
# Initialize clients
# ============================================================

content_safety_client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT,
    credential=AzureKeyCredential(CONTENT_SAFETY_KEY)
)

language_client = TextAnalyticsClient(
    endpoint=LANGUAGE_ENDPOINT,
    credential=AzureKeyCredential(LANGUAGE_KEY)
)

# ============================================================
# Read text file
# ============================================================


script_dir = os.path.dirname(os.path.abspath(__file__))
file_path = os.path.join(script_dir, "sample.txt")

# Load text from file
with open(file_path, "r", encoding="utf-8") as f:
    text_content = f.read()

print("="*70)
print("CONTENT ANALYSIS REPORT")
print("="*70)
print(f"\nOriginal Text Length: {len(text_content)} characters\n")

# ============================================================
# 1. CONTENT SAFETY ANALYSIS (Harmful Content Detection)
# ============================================================

print("="*70)
print("1. HARMFUL CONTENT DETECTION (Content Safety)")
print("="*70)

try:
    # Analyze for harmful content categories
    safety_request = AnalyzeTextOptions(
        text=text_content,
        categories=[
            TextCategory.HATE,      # Hate speech
            TextCategory.SEXUAL,    # Sexual content
            TextCategory.SELF_HARM, # Self-harm content
            TextCategory.VIOLENCE   # Violence
        ],
        output_type="FourSeverityLevels"  # Returns severity 0-6 scale
    )
    
    safety_response = content_safety_client.analyze_text(safety_request)
    
    print("\nCategory Analysis:")
    print("-" * 50)
    
    harmful_detected = False
    for category_result in safety_response.categories_analysis:
        severity_label = "SAFE" if category_result.severity == 0 else f"SEVERITY {category_result.severity}"
        status = "✓" if category_result.severity == 0 else "⚠"
        
        print(f"{status} {category_result.category:12s}: {severity_label}")
        
        if category_result.severity > 0:
            harmful_detected = True
    
    print("\n" + "-" * 50)
    if harmful_detected:
        print("⚠ WARNING: Potentially harmful content detected!")
    else:
        print("✓ PASS: No harmful content detected")
    
except Exception as e:
    print(f"❌ Error in Content Safety analysis: {e}")

# ============================================================
# 2. PII DETECTION (Personally Identifiable Information)
# ============================================================

print("\n" + "="*70)
print("2. PII DETECTION (Personally Identifiable Information)")
print("="*70)

try:
    # Detect PII entities
    documents = [text_content]
    pii_response = language_client.recognize_pii_entities(
        documents, 
        language="en",
        categories_filter=None  # Detect all PII categories
    )
    
    for idx, doc in enumerate(pii_response):
        if not doc.is_error:
            if len(doc.entities) > 0:
                print(f"\n⚠ WARNING: {len(doc.entities)} PII entities detected!\n")
                
                print("PII Entities Found:")
                print("-" * 50)
                
                # Group by category for better readability
                pii_by_category = {}
                for entity in doc.entities:
                    category = entity.category
                    if category not in pii_by_category:
                        pii_by_category[category] = []
                    pii_by_category[category].append({
                        'text': entity.text,
                        'subcategory': entity.subcategory,
                        'confidence': entity.confidence_score
                    })
                
                # Display grouped by category
                for category, entities in sorted(pii_by_category.items()):
                    print(f"\n{category}:")
                    for entity in entities:
                        subcategory_info = f" ({entity['subcategory']})" if entity['subcategory'] else ""
                        print(f"  • {entity['text']}{subcategory_info}")
                        print(f"    Confidence: {entity['confidence']:.2%}")
                
                print("\n" + "-" * 50)
                print("\nRedacted Text (PII Removed):")
                print("-" * 50)
                print(doc.redacted_text)
                
            else:
                print("\n✓ PASS: No PII detected")
        else:
            print(f"❌ Error: {doc.error}")

except Exception as e:
    print(f"❌ Error in PII detection: {e}")

# ============================================================
# 3. SUMMARY & RECOMMENDATIONS
# ============================================================

print("\n" + "="*70)
print("3. SUMMARY & RECOMMENDATIONS")
print("="*70)

print("\n📋 Analysis Complete:")
print("-" * 50)

# Check if content is safe to publish/send
is_safe_for_publish = True
recommendations = []

# Check harmful content
try:
    if any(cat.severity > 2 for cat in safety_response.categories_analysis):
        is_safe_for_publish = False
        recommendations.append("⚠ Review and moderate harmful content before publishing")
except:
    pass

# Check PII
try:
    if len(doc.entities) > 0:
        is_safe_for_publish = False
        sensitive_pii = [e for e in doc.entities if e.category in 
                        ['Email', 'PhoneNumber', 'Address', 'IPAddress', 
                         'CreditCard', 'BankAccount', 'SSN', 'ABARoutingNumber']]
        
        if sensitive_pii:
            recommendations.append(f"⚠ Remove or redact {len(sensitive_pii)} sensitive PII entities")
            recommendations.append("  Consider using the redacted text version")
except:
    pass

if is_safe_for_publish:
    print("\n✓ APPROVED: Content is safe for publishing/sending")
else:
    print("\n⚠ REQUIRES REVIEW: Content needs moderation")
    print("\nRecommendations:")
    for rec in recommendations:
        print(f"  {rec}")

print("\n" + "="*70)
print("END OF REPORT")
print("="*70)

# ============================================================
# Optional: Save detailed results to file
# ============================================================

# Uncomment to save results to a file
# with open("analysis_results.txt", "w", encoding="utf-8") as f:
#     f.write(f"Content Safety Results:\n{safety_response.as_dict()}\n\n")
#     f.write(f"PII Detection Results:\n")
#     for doc in pii_response:
#         if not doc.is_error:
#             f.write(f"Entities: {len(doc.entities)}\n")
#             f.write(f"Redacted Text:\n{doc.redacted_text}\n")