# Week 7 — Azure AI Language Services: Text Analytics

Hands-on demos for Azure AI Language Service covering key Text Analytics features.

---

## Setup

### 1. Install dependencies

```bash
pip install azure-ai-textanalytics python-dotenv
```

### 2. Configure credentials

Copy the example `.env` file and fill in the keys — **the instructor will share these in class**:

```bash
cp .env.example .env
```

Then open `.env` and set:

```
LANGUAGE_ENDPOINT=https://your-language-service.cognitiveservices.azure.com/
LANGUAGE_KEY=your-key-here
```

---

## Scripts

| # | Script | What it does |
|---|---|---|
| 1 | `1_LanguageDetection.py` | Detects the language of a given text |
| 2 | `2_KeyPhraseExtraction.py` | Extracts key topics and phrases from text |
| 3 | `3_NamedEntityRecognition.py` | Identifies and labels named entities (people, places, dates, etc.) |
| 4 | `4_LinkedEntityRecognition.py` | Recognises entities and links them to Wikipedia data sources |
| 5 | `5_PIIDetection.py` | Detects and redacts Personally Identifiable Information (PII) |
| 6 | `6_SentimentAnalysis.py` | Analyses sentiment (positive/neutral/negative) with opinion mining |
| 7 | `7_ExtractiveSummarization.py` | Extracts the most important sentences from a long document |

```bash
python 1_LanguageDetection.py
python 2_KeyPhraseExtraction.py
python 3_NamedEntityRecognition.py
python 4_LinkedEntityRecognition.py
python 5_PIIDetection.py
python 6_SentimentAnalysis.py
python 7_ExtractiveSummarization.py
```

---

## Archive

The `archive/` folder contains four Conversational Language Understanding (CLU) scripts that train and query custom NLU models:

- `1_CLU_Trainer_Menu.py` / `2_CLU_Trainer_GetTimeAndSend.py` — import, train, and deploy CLU projects to Azure
- `3_CLU_Client_Menu.py` / `4_CLU_Client_GetTimeAndSend.py` — query the deployed models with natural language

These are archived because CLU model training is currently blocked by an Azure backend bug where the evaluation step fails with an internal authentication error, preventing deployment via the SDK or REST API.
