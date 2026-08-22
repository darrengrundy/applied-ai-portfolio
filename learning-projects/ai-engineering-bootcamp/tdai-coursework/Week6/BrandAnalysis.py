# Azure Computer Vision - Brand Detection
# Detects brands/logos in images using modern API (v4.0+)

import os
import logging
from dotenv import load_dotenv
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

# ============================================================
# CONFIGURATION
# ============================================================

ENDPOINT = os.getenv("AZURE_VISION_ENDPOINT")
KEY = os.getenv("AZURE_VISION_KEY")


# ============================================================
# Initialize Client
# ============================================================

client = ImageAnalysisClient(
    endpoint=ENDPOINT,
    credential=AzureKeyCredential(KEY)
)

# ============================================================
# BRAND DETECTION - REMOTE URL
# ============================================================

print("="*80)
print("BRAND DETECTION - REMOTE IMAGE")
print("="*80)

# remote_image_url = "https://blog.logomyway.com/wp-content/uploads/2020/07/top-brand-logos.jpg"
remote_image_url = "https://th.bing.com/th/id/OIP.TgH53P1y0g2YQLGX9ufT_QHaEP?w=271&h=180&c=7&r=0&o=7&dpr=1.3&pid=1.7&rm=3"

print(f"\nAnalyzing: {remote_image_url}\n")

try:
    logger.info("Sending request to Azure Computer Vision...")
    result = client.analyze_from_url(
        image_url=remote_image_url,
        visual_features=[
            VisualFeatures.TAGS,     # Get tags 
            VisualFeatures.OBJECTS   # Get objects with bounding boxes
        ]
    )
    
    # Display detected tags (brands often appear here)
    if result.tags and len(result.tags.list) > 0:
        print("Detected tags (may include brands):")
        sorted_tags = sorted(result.tags.list, key=lambda x: x.confidence, reverse=True)
        for tag in sorted_tags[:10]:
            print(f"  • {tag.name}: {tag.confidence:.1%}")
    
    # Display detected objects (logos/brands with bounding boxes)
    if result.objects and len(result.objects.list) > 0:
        print(f"\nDetected objects with bounding boxes:")
        for obj in result.objects.list:
            bbox = obj.bounding_box
            print(f"  • '{obj.tags[0].name}' detected with confidence {obj.tags[0].confidence:.1%}")
            print(f"    Location: x={bbox.x}, y={bbox.y}, w={bbox.width}, h={bbox.height}")
    
    if not result.tags or len(result.tags.list) == 0:
        print("No brands/objects detected.")

except Exception as e:
    logger.error("Failed to analyse image: %s", e)

print()

# ============================================================
# BRAND DETECTION - LOCAL FILE (COMMENTED OUT)
# ============================================================
# Uncomment the section below to analyze local images

"""
print("="*80)
print("BRAND DETECTION - LOCAL IMAGE")
print("="*80)

local_image_path = ".\\Brand_Images\\s-l960.jpg"

print(f"\nAnalyzing local file: {local_image_path}\n")

try:
    # Read local image file
    with open(local_image_path, "rb") as image_file:
        image_data = image_file.read()
    
    # Analyze local image
    result = client.analyze(
        image_data=image_data,
        visual_features=[
            VisualFeatures.TAGS,
            VisualFeatures.OBJECTS
        ]
    )
    
    # Display detected tags (brands often appear here)
    if result.tags and len(result.tags.list) > 0:
        print("Detected tags (may include brands):")
        sorted_tags = sorted(result.tags.list, key=lambda x: x.confidence, reverse=True)
        for tag in sorted_tags[:10]:
            print(f"  • {tag.name}: {tag.confidence:.1%}")
    
    # Display detected objects (logos/brands with bounding boxes)
    if result.objects and len(result.objects.list) > 0:
        print(f"\nDetected objects with bounding boxes:")
        for obj in result.objects.list:
            bbox = obj.bounding_box
            print(f"  • '{obj.tags[0].name}' detected with confidence {obj.tags[0].confidence:.1%}")
            print(f"    Location: x={bbox.x}, y={bbox.y}, w={bbox.width}, h={bbox.height}")
    
    if not result.tags or len(result.tags.list) == 0:
        print("No brands/objects detected.")
        
except FileNotFoundError:
    print(f"Error: File not found at {local_image_path}")
except Exception as e:
    print(f"Error: {e}")

print()
"""

# ============================================================
# NOTE ABOUT BRAND DETECTION
# ============================================================

print("\n" + "="*80)
print("NOTE: Dedicated brand detection is no longer available")
print("="*80)
print("""
The new Computer Vision API (v4.0+) does not have a dedicated 'brands' feature.

Instead, brands are detected through:
1. TAGS feature - Brand names appear as tags
2. OBJECTS feature - Logos detected as objects with bounding boxes

This approach works well for most brand/logo detection scenarios.
""")