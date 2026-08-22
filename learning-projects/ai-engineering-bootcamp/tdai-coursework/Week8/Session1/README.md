# Week 8 Session 1 — Document Intelligence & Content Understanding

Hands-on demos using Azure Document Intelligence and Azure AI Content Understanding to read, structure, and extract data from real-world documents with zero model training.

## Scripts

| Script | Service | What it does |
|--------|---------|-------------|
| `1_DocIntelligence_BusinessCard.py` | Document Intelligence `prebuilt-read` | OCR — extracts every line of text from a business card |
| `2_DocIntelligence_Layout.py` | Document Intelligence `prebuilt-layout` | Detects key-value pairs on a business card |
| `3_ContentUnderstanding_BusinessCard.py` | Content Understanding (custom schema) | Extracts specific fields defined in `biz-card-schema.json` |
| `4_InvoiceAnalysis.py` | Document Intelligence `prebuilt-invoice` | Extracts 23+ fields from invoices — vendor, customer, line items, totals |

## Prerequisites

- Python 3.11 or later
- An **Azure Document Intelligence** resource (for scripts 1, 2, 4)
  - Create one at [portal.azure.com](https://portal.azure.com/#create/Microsoft.CognitiveServicesFormRecognizer)
  - Recommended region: East US
  - Free tier (F0) is sufficient for demos
- An **Azure AI Services** resource connected to Content Understanding Studio (for script 3)
  - Must be in a supported region: East US, East US 2, West US, West US 3, West Europe, North Europe, UK South, Sweden Central, Australia East, Japan East, South Central US, or Southeast Asia
  - Set up at [contentunderstanding.ai.azure.com](https://contentunderstanding.ai.azure.com)

## Setup

### 1. Get the repo

If you have not cloned the repo yet:

```bash
git clone https://github.com/TDAI-admin/AI-Engineering-TDAI.git
cd AI-Engineering-TDAI/Week8/Session1
```

If you already cloned it, pull the latest:

```bash
git pull
cd Week8/Session1
```

### 2. Create and activate a virtual environment

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install azure-ai-documentintelligence azure-ai-contentunderstanding python-dotenv
```

### 4. Configure credentials

Copy the example env file:

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your values:

```
# For scripts 1, 2, 4 — Azure Document Intelligence
DOC_INTELLIGENCE_ENDPOINT=https://<your-resource-name>.cognitiveservices.azure.com/
DOC_INTELLIGENCE_KEY=<your-key-here>

# For script 3 — Azure AI Content Understanding
CONTENT_UNDERSTANDING_ENDPOINT=https://<your-resource-name>.services.ai.azure.com
CONTENT_UNDERSTANDING_KEY=<your-key-here>
ANALYZER_NAME=businesscardanalyser
```

Where to find these: **Azure Portal** → your resource → **Keys and Endpoint**

### 5. Content Understanding Studio setup (script 3 only)

Before running script 3 for the first time:

1. Go to [contentunderstanding.ai.azure.com](https://contentunderstanding.ai.azure.com)
2. Sign in with your Azure account
3. Click **Add a resource** and select your Azure AI Services resource
4. Tick **Enable auto-deployment** — this deploys the required `gpt-4.1` and `text-embedding-3-large` models
5. Click **Save**

This step only needs to be done once per resource.

## Running the Demos

```bash
python 1_DocIntelligence_BusinessCard.py
python 2_DocIntelligence_Layout.py
python 3_ContentUnderstanding_BusinessCard.py
python 4_InvoiceAnalysis.py
```

## Sample Files

| Folder | Files |
|--------|-------|
| `sample_cards/` | `adventure_works.jpg`, `contoso.jpg` |
| `sample_invoices/` | `invoice-contoso.png`, `invoice-hero.png`, `sample-invoice.pdf` |

You can drop your own `.jpg`, `.png`, or `.pdf` files into either folder and the scripts will pick them up automatically.

## Expected Output

**Demo 1 — Business Card OCR:**

```
adventure_works.jpg
  Lines found: 11
    Dr. Avery Smith
    Senior Researcher
    Cloud & AI Department
    avery.smith@contoso.com
    mob: +44 (0) 7911 123456
```

**Demo 2 — Layout Key-Value Pairs:**

```
contoso.jpg
  KEY                  VALUE
  Email:               marie@contoso.com  (confidence: 93%)
  Phone:               555-010-9876  (confidence: 100%)
```

**Demo 3 — Content Understanding (Custom Schema):**

```
adventure_works.jpg
  Company   : Contoso
  Name      : Dr. Avery Smith
  Title     : Senior Researcher
  Email     : avery.smith@contoso.com
  Phone     : +44 (0) 7911 123456
```

**Demo 4 — Invoice Extraction:**

```
sample-invoice.pdf
  Vendor       : CONTOSO LTD.
  Customer     : MICROSOFT CORPORATION
  Invoice #    : INV-100
  Invoice Date : 2019-11-15
  Due Date     : 2019-12-15
  P.O. Number  : PO-3333

  DESCRIPTION                           QTY        UNIT       TOTAL
  Test for 23 fields                      1       $1.00     $100.00

  Subtotal                $100.00
  Tax                      $10.00
  TOTAL                   $110.00
```

## Key Concepts

**prebuilt-read** extracts raw text using OCR. Works on any document. Every line is treated equally — no structure assumed.

**prebuilt-layout** understands document structure and detects key-value pairs. When a card has a label like `Email:` next to a value, the model links them together with a confidence score.

**Content Understanding** lets you define a custom JSON schema specifying exactly which fields to extract. The model reasons from context — it doesn't need the field label to appear on the document. Changing the schema changes what gets extracted, with no retraining.

**prebuilt-invoice** is purpose-built for invoices. Returns 23+ named fields and line item arrays without any configuration or training.

## Resources

- [Azure Document Intelligence documentation](https://learn.microsoft.com/azure/ai-services/document-intelligence/)
- [Prebuilt models overview](https://learn.microsoft.com/azure/ai-services/document-intelligence/concept-model-overview)
- [Content Understanding documentation](https://learn.microsoft.com/azure/ai-services/content-understanding/)
- [Microsoft Learn lab — Content Understanding API](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/02-content-understanding-api.html)
- [Microsoft Learn lab — Prebuilt Document Intelligence](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Labs/03-prebuilt-doc-intelligence-model.html)
