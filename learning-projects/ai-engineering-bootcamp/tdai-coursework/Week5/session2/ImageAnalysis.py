# Azure AI Image Content Safety + OCR + Face Detection
# Replaces deprecated Azure Content Moderator for images
# https://learn.microsoft.com/en-us/azure/ai-services/content-safety/
# https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/

import sys
import os
sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
from pprint import pprint
from azure.ai.contentsafety import ContentSafetyClient
from azure.ai.contentsafety.models import AnalyzeImageOptions, ImageData, ImageCategory
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
import requests
from io import BytesIO
import base64

load_dotenv()

# Azure AI Content Safety credentials (for harmful content detection)
CONTENT_SAFETY_KEY = os.getenv("AZURE_CONTENT_SAFETY_KEY")
CONTENT_SAFETY_ENDPOINT = os.getenv("AZURE_CONTENT_SAFETY_ENDPOINT")

# Azure Computer Vision credentials (for OCR and face detection)
COMPUTER_VISION_ENDPOINT = os.getenv("AZURE_COMPUTER_VISION_ENDPOINT")
COMPUTER_VISION_KEY = os.getenv("AZURE_COMPUTER_VISION_KEY")
# ============================================================
# Initialize clients
# ============================================================

content_safety_client = ContentSafetyClient(
    endpoint=CONTENT_SAFETY_ENDPOINT,
    credential=AzureKeyCredential(CONTENT_SAFETY_KEY)
)

computer_vision_client = ImageAnalysisClient(
    endpoint=COMPUTER_VISION_ENDPOINT,
    credential=AzureKeyCredential(COMPUTER_VISION_KEY)
)

# ============================================================
# Test Images
# ============================================================

IMAGE_LIST = [
    "https://content.api.news/v3/images/bin/756692568a236c94619b202e9b68687a?width=650",
    "https://mockuptree.com/wp-content/uploads/edd/2022/01/minecraft-text-effect-psd.jpg",
    "https://media.istockphoto.com/id/1550540247/photo/decision-thinking-and-asian-man-in-studio-with-glasses-questions-and-brainstorming-on-grey.jpg?s=2048x2048&w=is&k=20&c=AHKcPCjnl3pP21Kl9G8JA4N22lZLICuoyKlJTHU9D-E="
]

# ============================================================
# Helper function to download image as base64
# ============================================================

def download_image_as_base64(image_url):
    """Download image from URL and convert to base64 string"""
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()
        image_bytes = response.content
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        return base64_image
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

# ============================================================
# Process each image
# ============================================================

for idx, image_url in enumerate(IMAGE_LIST, 1):
    print("\n" + "="*80)
    print(f"IMAGE {idx}/{len(IMAGE_LIST)}: {image_url}")
    print("="*80)
    
    # Download image as base64 (required for Content Safety)
    print("\n📥 Downloading image...")
    base64_image = download_image_as_base64(image_url)
    
    if not base64_image:
        print("❌ Failed to download image. Skipping...")
        continue
    
    print("✓ Image downloaded successfully")
    
    # ================================================================
    # 1. CONTENT SAFETY ANALYSIS (Adult/Racy/Violent content)
    # ================================================================
    
    print("\n" + "-"*80)
    print("1. HARMFUL CONTENT DETECTION (Adult, Violence, Hate)")
    print("-"*80)
    
    try:
        # Analyze image for harmful content
        request = AnalyzeImageOptions(
            image=ImageData(content=base64_image),
            categories=[
                ImageCategory.HATE,
                ImageCategory.SELF_HARM,
                ImageCategory.SEXUAL,
                ImageCategory.VIOLENCE
            ],
            output_type="FourSeverityLevels"  # 0-6 severity scale
        )
        
        response = content_safety_client.analyze_image(request)
        
        print("\nCategory Analysis:")
        harmful_detected = False
        
        for category_result in response.categories_analysis:
            severity_label = "SAFE" if category_result.severity == 0 else f"SEVERITY {category_result.severity}"
            status = "✓" if category_result.severity == 0 else "⚠"
            
            print(f"{status} {category_result.category:12s}: {severity_label}")
            
            if category_result.severity > 0:
                harmful_detected = True
        
        if harmful_detected:
            print("\n⚠ WARNING: Potentially inappropriate content detected!")
        else:
            print("\n✓ PASS: Image appears safe")
            
    except Exception as e:
        print(f"❌ Error in Content Safety analysis: {e}")
    
    # ================================================================
    # 2. OCR - TEXT EXTRACTION
    # ================================================================
    
    print("\n" + "-"*80)
    print("2. TEXT EXTRACTION (OCR)")
    print("-"*80)
    
    try:
        # Use Computer Vision for OCR (Read API)
        result = computer_vision_client.analyze_from_url(
            image_url=image_url,
            visual_features=[VisualFeatures.READ]
        )
        
        if result.read and result.read.blocks:
            print(f"\n✓ Text detected in image!")
            print(f"\nTotal blocks: {len(result.read.blocks)}")
            
            all_text = []
            for block_idx, block in enumerate(result.read.blocks, 1):
                print(f"\n--- Block {block_idx} ---")
                for line in block.lines:
                    print(f"  {line.text}")
                    all_text.append(line.text)
            
            print(f"\nFull extracted text:\n{' '.join(all_text)}")
            
        else:
            print("\n✓ No text detected in image")
            
    except Exception as e:
        print(f"❌ Error in OCR: {e}")
    
    # ================================================================
    # 3. FACE DETECTION
    # ================================================================
    
    print("\n" + "-"*80)
    print("3. FACE DETECTION")
    print("-"*80)
    
    try:
        # Use Computer Vision for face detection
        result = computer_vision_client.analyze_from_url(
            image_url=image_url,
            visual_features=[VisualFeatures.PEOPLE]
        )
        
        if result.people and result.people.list:
            print(f"\n✓ {len(result.people.list)} person(s) detected!")
            
            for person_idx, person in enumerate(result.people.list, 1):
                print(f"\nPerson {person_idx}:")
                print(f"  Confidence: {person.confidence:.2%}")
                if person.bounding_box:
                    bbox = person.bounding_box
                    print(f"  Bounding Box: x={bbox.x}, y={bbox.y}, w={bbox.width}, h={bbox.height}")
        else:
            print("\n✓ No faces detected in image")
            
    except Exception as e:
        print(f"❌ Error in face detection: {e}")
    
    # ================================================================
    # SUMMARY FOR THIS IMAGE
    # ================================================================
    
    print("\n" + "="*80)
    print(f"SUMMARY - Image {idx}")
    print("="*80)
    
    try:
        is_safe = all(cat.severity == 0 for cat in response.categories_analysis)
        has_text = result.read and result.read.blocks
        has_faces = result.people and result.people.list
        
        print(f"Safety Status: {'✓ SAFE' if is_safe else '⚠ FLAGGED'}")
        print(f"Text Detected: {'Yes' if has_text else 'No'}")
        print(f"Faces Detected: {len(result.people.list) if has_faces else 0}")
        
    except:
        print("Unable to generate complete summary")

print("\n" + "="*80)
print("ALL IMAGES PROCESSED")
print("="*80)