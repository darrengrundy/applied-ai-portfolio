# Azure Computer Vision - Landmark Detection
# Uses TAGS feature to identify famous landmarks

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
# Images to Analyze
# ============================================================

IMAGES = [
    "https://images.unsplash.com/photo-1564507592333-c60657eea523?q=80&w=2071&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
    "https://lh3.googleusercontent.com/p/AF1QipMHftgSCBlvyjxYphi4gLqDC_62WWvZvyy1EBuh=s1360-w1360-h1020",
    "https://assets.editorial.aetnd.com/uploads/2015/02/topic-golden-gate-bridge-gettyimages-177770941.jpg?width=1920&height=960&crop=1920%3A960%2Csmart&quality=75&auto=webp",
    "https://st.depositphotos.com/1759109/1331/i/450/depositphotos_13315503-stock-photo-tower-bridge-at-dusk.jpg",
    "https://images.unsplash.com/photo-1599676603816-0f92b2d713d2?q=80&w=1000&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8M3x8dG93ZXIlMjBicmlkZ2V8ZW58MHx8MHx8fDA%3D"
]

# ============================================================
# Analyze Images
# ============================================================

print("\n" + "="*80)
print("LANDMARK DETECTION")
print("="*80)

for idx, image_url in enumerate(IMAGES, 1):
    print(f"\nImage {idx}: {image_url[:60]}...")
    
    try:
        logger.info("Analysing image %d/%d...", idx, len(IMAGES))
        result = client.analyze_from_url(
            image_url=image_url,
            visual_features=[VisualFeatures.TAGS]
        )
        
        # Display top tags
        if result.tags and len(result.tags.list) > 0:
            print("Detected tags:")
            
            # Sort by confidence and show top 5
            sorted_tags = sorted(result.tags.list, key=lambda x: x.confidence, reverse=True)
            for tag in sorted_tags[:5]:
                print(f"  • {tag.name}: {tag.confidence:.2%}")
        else:
            print("  No tags detected")
            
    except Exception as e:
        logger.error("Failed to analyse image %d: %s", idx, e)

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)