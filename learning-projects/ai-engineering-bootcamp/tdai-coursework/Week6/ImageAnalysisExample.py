# Azure Computer Vision - Complete Image Analysis
# Modern version using azure-ai-vision-imageanalysis
# https://learn.microsoft.com/en-us/azure/ai-services/computer-vision/how-to/call-analyze-image-40

import os
import logging
from dotenv import load_dotenv
from azure.ai.vision.imageanalysis import ImageAnalysisClient
from azure.ai.vision.imageanalysis.models import VisualFeatures
from azure.core.credentials import AzureKeyCredential
from pprint import pprint

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
# Test Images - Different scenarios
# ============================================================

TEST_IMAGES = [
    {
        "name": "Taj Mahal (UNESCO Site)",
        "url": "https://images.unsplash.com/photo-1564507592333-c60657eea523?q=80&w=2071&auto=format&fit=crop&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D",
        "description": "Historic monument with text and architecture"
    },
    {
        "name": "Nature Landscape",
        "url": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4",
        "description": "Mountain landscape without text or people"
    },
    {
        "name": "Text-Heavy Image",
        "url": "https://mockuptree.com/wp-content/uploads/edd/2022/01/minecraft-text-effect-psd.jpg",
        "description": "Image with prominent text overlay"
    }
]

# ============================================================
# Visual Features Configuration
# ============================================================

# All available visual features
# Note: CAPTION and DENSE_CAPTIONS are not supported in Australia East region
VISUAL_FEATURES = [
    VisualFeatures.TAGS,            # Image tags/labels
    VisualFeatures.OBJECTS,         # Object detection with bounding boxes
    VisualFeatures.READ,            # OCR - text extraction
    VisualFeatures.SMART_CROPS,     # Intelligent cropping suggestions
    VisualFeatures.PEOPLE,          # People detection
]

# Smart crop aspect ratios (common use cases)
ASPECT_RATIOS = [
    0.9,   # Nearly square (Instagram post)
    1.33,  # 4:3 (Traditional)
    1.78,  # 16:9 (Widescreen)
]

# ============================================================
# Helper Function - Pretty Print Results
# ============================================================

def analyze_and_display_image(image_info):
    """Analyze an image and display comprehensive results"""
    
    print("\n" + "="*80)
    print(f"ANALYZING: {image_info['name']}")
    print("="*80)
    print(f"URL: {image_info['url']}")
    print(f"Description: {image_info['description']}")
    print("-"*80)
    
    try:
        logger.info("Analysing: %s", image_info['name'])
        result = client.analyze_from_url(
            image_url=image_info['url'],
            visual_features=VISUAL_FEATURES,
            smart_crops_aspect_ratios=ASPECT_RATIOS,
            gender_neutral_caption=True,  # Use inclusive language
            language="en"
        )
        
        # ====================================================
        # 1. IMAGE METADATA
        # ====================================================
        print("\n[METADATA]")
        print("-"*80)
        print(f"Dimensions: {result.metadata.width}x{result.metadata.height} pixels")
        print(f"Model Version: {result.model_version}")
        
        # ====================================================
        # 2. TAGS (Keywords/Labels)
        # ====================================================
        if result.tags is not None:
            print("\n[TAGS] Image Labels")
            print("-"*80)
            sorted_tags = sorted(result.tags.list, key=lambda x: x.confidence, reverse=True)
            for idx, tag in enumerate(sorted_tags[:15], 1):  # Top 15 tags
                confidence_bar = "#" * int(tag.confidence * 20)
                print(f"{idx:2d}. {tag.name:25s} {confidence_bar} {tag.confidence:.2%}")

        # ====================================================
        # 3. OBJECTS (Detected objects with locations)
        # ====================================================
        if result.objects is not None:
            print("\n[OBJECTS] Detected")
            print("-"*80)
            if len(result.objects.list) > 0:
                for idx, obj in enumerate(result.objects.list, 1):
                    print(f"\n{idx}. Object: {obj.tags[0].name}")
                    print(f"   Confidence: {obj.tags[0].confidence:.2%}")
                    print(f"   Bounding Box: {obj.bounding_box}")
            else:
                print("No objects detected")

        # ====================================================
        # 4. PEOPLE DETECTION
        # ====================================================
        if result.people is not None:
            print("\n[PEOPLE] Detected")
            print("-"*80)
            if len(result.people.list) > 0:
                print(f"Total people found: {len(result.people.list)}\n")
                for idx, person in enumerate(result.people.list, 1):
                    print(f"Person {idx}:")
                    print(f"   Confidence: {person.confidence:.2%}")
                    print(f"   Location: {person.bounding_box}")
            else:
                print("No people detected in this image")

        # ====================================================
        # 5. TEXT EXTRACTION (OCR)
        # ====================================================
        if result.read is not None:
            print("\n[OCR] Text Extraction")
            print("-"*80)

            if len(result.read.blocks) > 0:
                all_text = []
                for block_idx, block in enumerate(result.read.blocks, 1):
                    print(f"\nText Block {block_idx}:")
                    for line_idx, line in enumerate(block.lines, 1):
                        print(f"  Line {line_idx}: '{line.text}'")
                        print(f"    Bounding: {line.bounding_polygon}")
                        all_text.append(line.text)

                print(f"\nFull Extracted Text:\n{' '.join(all_text)}")
            else:
                print("No text detected in this image")

        # ====================================================
        # 6. SMART CROPS (Intelligent cropping suggestions)
        # ====================================================
        if result.smart_crops is not None:
            print("\n[SMART CROPS] Suggestions")
            print("-"*80)
            print("Optimal cropping regions for different aspect ratios:\n")
            for crop in result.smart_crops.list:
                ratio_name = {
                    0.9: "Square (Instagram)",
                    1.33: "4:3 (Traditional)",
                    1.78: "16:9 (Widescreen)"
                }.get(crop.aspect_ratio, f"Custom ({crop.aspect_ratio})")

                print(f"  {ratio_name}")
                print(f"   Aspect Ratio: {crop.aspect_ratio}")
                print(f"   Bounding Box: {crop.bounding_box}\n")

        # ====================================================
        # SUMMARY
        # ====================================================
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY")
        print("="*80)

        summary = []
        if result.tags: summary.append(f"+ {len(result.tags.list)} tags identified")
        if result.objects: summary.append(f"+ {len(result.objects.list)} objects detected")
        if result.people: summary.append(f"+ {len(result.people.list)} people detected")
        if result.read and len(result.read.blocks) > 0: summary.append(f"+ Text found in {len(result.read.blocks)} blocks")
        if result.smart_crops: summary.append(f"+ {len(result.smart_crops.list)} smart crop suggestions")

        for item in summary:
            print(f"  {item}")

        return True

    except Exception as e:
        logger.error("Failed to analyse %s: %s", image_info['name'], e)
        return False

# ============================================================
# Main Execution
# ============================================================

def main():
    """Run comprehensive image analysis on all test images"""
    
    print("\n" + "="*80)
    print("AZURE COMPUTER VISION - COMPREHENSIVE IMAGE ANALYSIS")
    print("="*80)
    print("\nAnalyzing multiple images with all visual features:")
    print("  - Tags & Labels")
    print("  - Object Detection")
    print("  - People Detection")
    print("  - Text Extraction (OCR)")
    print("  - Smart Crop Suggestions")
    print("  Note: Caption/Dense Captions not supported in Australia East region")
    
    # Analyze each test image
    success_count = 0
    for image_info in TEST_IMAGES:
        if analyze_and_display_image(image_info):
            success_count += 1
    
    # Final summary
    print("\n" + "="*80)
    print("BATCH ANALYSIS COMPLETE")
    print("="*80)
    print(f"Successfully analyzed: {success_count}/{len(TEST_IMAGES)} images")
    
    print("\nKey Insights:")
    print("  - TAGS: Best for searchability and categorization")
    print("  - OBJECTS: Best for counting and locating specific items")
    print("  - PEOPLE: Best for counting people or detecting faces")
    print("  - READ: Best for extracting any text in the image")
    print("  - SMART_CROPS: Best for automated image cropping")

# ============================================================
# Alternative: Analyze Local Image
# ============================================================

def analyze_local_image(image_path):
    """Analyze an image from local filesystem"""
    
    print(f"\nAnalyzing local image: {image_path}")
    
    try:
        with open(image_path, "rb") as image_file:
            image_data = image_file.read()
        
        result = client.analyze(
            image_data=image_data,
            visual_features=VISUAL_FEATURES,
            smart_crops_aspect_ratios=ASPECT_RATIOS,
            language="en"
        )

        if result.tags:
            print(f"\nTop Tags:")
            for tag in sorted(result.tags.list, key=lambda x: x.confidence, reverse=True)[:5]:
                print(f"  • {tag.name} ({tag.confidence:.2%})")
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return None

# ============================================================
# Run the Analysis
# ============================================================

if __name__ == "__main__":
    # Run batch analysis on test images
    main()
    
    # Optional: Analyze a local image
    # Uncomment and provide path to analyze local images:
    # analyze_local_image("path/to/your/image.jpg")