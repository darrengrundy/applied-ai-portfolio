# Week 6 — Azure Computer Vision & Custom Vision

This week covers image analysis and custom model training using Azure AI Vision services.

---

## Prerequisites

Activate the shared virtual environment from the repo root before running anything:

```bash
# From the repo root
.venv\Scripts\activate        # Windows
source .venv/bin/activate     # Mac/Linux
```

Install the required packages:

```bash
pip install azure-ai-vision-imageanalysis azure-cognitiveservices-vision-customvision msrest python-dotenv
```

### Environment Variables

All credentials are stored in a `.env` file. Copy the example and fill in your values:

```bash
cp Week6/.env.example Week6/.env
```

Then open `Week6/.env` and fill in the keys for the Azure resources listed at the bottom of this README.

### Running Scripts

All scripts are run from the **repo root** (not from inside `Week6/`):

```bash
# Example
python Week6/OCR.py
```

> `LocalOCR.py` specifically requires you to run from the repo root because it references `Week6/Handwritten_Notes/` as a relative path.

---

## Scripts

### 1. OCR — `OCR.py`

Extracts text from a remote image URL using Azure Computer Vision's READ feature.

```bash
python Week6/OCR.py
```

---

### 2. Local OCR — `LocalOCR.py`

Extracts text from a local handwritten notes image (`Week6/Handwritten_Notes/20240201_201437_1.jpg`).

```bash
python Week6/LocalOCR.py
```

---

### 3. Image Analysis — `ImageAnalysisExample.py`

Runs a comprehensive analysis across 3 test images, demonstrating:
- **Tags** — keyword labels with confidence scores
- **Object Detection** — objects with bounding boxes
- **People Detection** — person count and locations
- **OCR** — text extraction
- **Smart Crops** — optimal crop regions for different aspect ratios

> Note: Caption and Dense Captions features are not supported in the Australia East region and have been excluded.

```bash
python Week6/ImageAnalysisExample.py
```

---

### 4. Landmark Detection — `LandmarkDetection.py`

Identifies famous landmarks in 5 images by analysing their tags.

```bash
python Week6/LandmarkDetection.py
```

---

### 5. Brand Detection — `BrandAnalysis.py`

Detects brands and logos in images using the TAGS and OBJECTS features.

> Note: The Computer Vision v4.0+ API does not have a dedicated brands feature — brands are detected through tags and object labels instead.

```bash
python Week6/BrandAnalysis.py
```

---

### 6. Custom Vision — Image Classification — `CustomVision.py`

Trains a custom image classification model to distinguish between **Hemlock** and **Japanese Cherry** trees, then runs a test prediction.

The script:
1. Deletes any existing projects on the resource (clean slate)
2. Creates a new project and uploads 20 labelled images (10 per class) from `Week6/Images/`
3. Trains the model (takes ~3-5 minutes)
4. Publishes the iteration and runs a prediction on `Week6/Images/Test/test_image.jpg`

```bash
python Week6/CustomVision.py
```

Expected output:
```
Japanese Cherry: 100.00%
Hemlock: 0.00%
```

---

### 7. Custom Vision — Object Detection — `ObjectDetection_CustomVision.py`

Trains a custom object detection model to locate **forks** and **scissors** in images with bounding boxes, then runs a test prediction.

The script:
1. Deletes any existing projects on the resource (clean slate)
2. Creates a new project and uploads 40 labelled images (20 per class) from `Week6/Images_Obj_Detection/` with normalised bounding box coordinates
3. Trains the model (takes ~3-5 minutes)
4. Publishes the iteration and runs a prediction on `Week6/Images_Obj_Detection/test/test_image.jpg`

```bash
python Week6/ObjectDetection_CustomVision.py
```

Expected output:
```
fork: 80.24% bbox.left=0.05, bbox.top=0.20, bbox.width=0.71, bbox.height=0.66
...
```

---

## Azure Resources Used

| Script(s) | Resource | Service |
|---|---|---|
| `OCR.py`, `LocalOCR.py`, `ImageAnalysisExample.py`, `LandmarkDetection.py`, `BrandAnalysis.py` | `tdai-foundry` (Australia East) | Azure AI Vision (Image Analysis v4.0) |
| `CustomVision.py`, `ObjectDetection_CustomVision.py` | `tdaicustomvision` + `tdaicustomvision-prediction` (Australia East) | Azure Custom Vision |

> Credentials are loaded from `Week6/.env` — never commit that file.
