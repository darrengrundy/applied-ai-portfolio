# Week 7 — TA Setup Guide: Azure Resources & Model Deployments

This guide covers everything that needs to be provisioned in Azure **before class** so that all demos run without interruption. It covers both Session 1 (Language) and Session 2 (Speech).

---

## Overview

| Session | Azure Resource | Model Deployments in Foundry |
|---|---|---|
| Session 1 | Azure AI Language Service | None (pre-built APIs) |
| Session 2 (scripts 1–5) | Azure AI Foundry hub + project | `gpt-4o-mini` |
| Session 2 (scripts 6–7) | Azure OpenAI resource | `gpt-4o-mini-tts`, `gpt-4o-mini-transcribe` |
| Session 2 (script 8) | Azure AI Services (multi-service) | `gpt-5.3-chat` (used via Voice Live) |

---

## Session 1 — Azure AI Language Service

### Resource to Create

| Field | Value |
|---|---|
| **Resource type** | Azure AI Language Service |
| **Pricing tier** | S (Standard) — Free tier has rate limits that will cause issues in class |
| **Region** | Any (e.g. `australiaeast` or `eastus`) — just be consistent |

### Steps
1. Go to **Azure Portal** → Create a resource → search **Language service**
2. Select features: leave all defaults on (includes CLU, Text Analytics, etc.)
3. After creation, go to **Keys and Endpoint** and copy:
   - `KEY 1`
   - `Endpoint`

### What to share with students
Paste both values at the top of every script in `Week7/Session1/`. All 11 scripts use the **same key and endpoint**.

### Model Deployments
**None required.** All Session 1 APIs are pre-built:
- CLU (scripts 1–4): custom models are trained and deployed **by the trainer scripts themselves** via the API — nothing to do in the portal beforehand.
- Text Analytics (scripts 5–11): zero-config, call the endpoint directly.

---

## Session 2 — Azure AI Speech

Session 2 needs **three separate Azure resources**. Each covers a different set of scripts.

---

### Resource A — Azure AI Foundry Hub + Project
**Used by:** scripts 2, 3, 4, 5 (and the portal voice demo before script 8)

#### Steps
1. Go to [https://ai.azure.com](https://ai.azure.com) → **+ New hub**
   - Region: `australiaeast`
   - This automatically creates an Azure AI Services resource underneath it
2. Inside the hub, create a **project** (e.g. `tdai-voice-demo`)
3. In the project sidebar → **Models + endpoints** → **+ Deploy model**

#### Model to Deploy

| Deployment name | Model | SKU |
|---|---|---|
| `gpt-4o-mini` | `gpt-4o-mini` | Standard |

> The deployment name must match the `FOUNDRY_MODEL` env var (default: `gpt-4o-mini`).

#### Keys to copy
- **Project Settings → Overview → Project endpoint** → `FOUNDRY_ENDPOINT`
  - Format: `https://<hub-name>.services.ai.azure.com/api/projects/<project-name>`
- **Project Settings → Overview → Keys** → `FOUNDRY_KEY`
- **Hub region** → `SPEECH_REGION` (e.g. `australiaeast`)

> **Important:** The `FOUNDRY_KEY` and `SPEECH_REGION` are also used by the **Speech SDK** in scripts 2–5. The Azure AI Foundry resource is a multi-service resource, so its key works directly with `SpeechConfig(subscription=FOUNDRY_KEY, region=SPEECH_REGION)`.

#### What to share with students
Fill in the `.env` file in `Week7/Session2/`:
```
FOUNDRY_KEY=<key from Foundry project>
FOUNDRY_ENDPOINT=https://<hub>.services.ai.azure.com/api/projects/<project>
SPEECH_REGION=australiaeast
FOUNDRY_MODEL=gpt-4o-mini
```

---

### Resource B — Azure OpenAI (Speech models)
**Used by:** script 6 (`gpt-4o-mini-tts`) and script 7 (`gpt-4o-mini-transcribe`)

These are **different models** from the standard chat models and require a **separate Azure OpenAI resource** deployed in a region that supports audio models.

#### Steps
1. Azure Portal → Create a resource → **Azure OpenAI**
   - Region: `eastus` or `swedencentral` (audio models have limited regional availability — check the Azure model availability page)
   - Pricing tier: Standard S0
2. After creation → **Azure OpenAI Studio** (or **Foundry Models + Endpoints**) → **Deploy model**

#### Models to Deploy

| Deployment name | Model | Notes |
|---|---|---|
| `gpt-4o-mini-tts` | `gpt-4o-mini-tts` | Text-to-Speech with tone/instruction control |
| `gpt-4o-mini-transcribe` | `gpt-4o-mini-transcribe` | Audio transcription (Whisper-class) |

#### Keys to copy
- **Resource → Keys and Endpoint**:
  - `AZURE_OPENAI_SPEECH_ENDPOINT` — the endpoint URL
  - `AZURE_OPENAI_SPEECH_KEY` — Key 1

#### What to share with students
```
AZURE_OPENAI_SPEECH_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com
AZURE_OPENAI_SPEECH_KEY=<key>
```

> Script 6 and 7 both use `api_version="2025-03-01-preview"` — make sure this version is available for your resource.

---

### Resource C — Azure AI Services (Voice Live)
**Used by:** script 8 (`8_VoiceLiveAgent.py`) and the portal voice demo (`FOUNDRY_PORTAL_GUIDE.md`)

Voice Live is a real-time WebSocket-based service. It requires an **Azure AI Services multi-service resource** (not a standalone Speech resource).

#### Steps
1. Azure Portal → Create a resource → **Azure AI Services** (multi-service)
   - Region: `eastus` or another region where Voice Live is available
   - Pricing tier: S0
2. No additional model deployment steps — Voice Live uses the model name passed at connection time via the SDK.

#### Model used
The model is specified at runtime via the `VOICELIVE_MODEL` env var:

| Env var | Value |
|---|---|
| `VOICELIVE_MODEL` | `gpt-5.3-chat` |

> This model is served by Azure's Voice Live infrastructure — it is **not** something you deploy manually. You just pass the name and Azure routes it. Confirm the exact model name is still `gpt-5.3-chat` by checking the Azure Voice Live documentation at class time, as preview model names can change.

#### Keys to copy
- **Resource → Keys and Endpoint**:
  - `VOICELIVE_ENDPOINT` — base URL only, no path (e.g. `https://<name>.cognitiveservices.azure.com`)
  - `VOICELIVE_KEY` — Key 1

#### What to share with students
```
VOICELIVE_ENDPOINT=https://<resource-name>.cognitiveservices.azure.com
VOICELIVE_KEY=<key>
VOICELIVE_MODEL=gpt-5.3-chat
```

---

## Complete `.env` for Session 2

Here is what the final `.env` file should look like (fill in all values before class):

```env
# Scripts 2, 3, 4, 5 — Azure AI Foundry (Speech SDK + Chat)
FOUNDRY_KEY=<azure-ai-foundry-key>
FOUNDRY_ENDPOINT=https://<hub>.services.ai.azure.com/api/projects/<project>
SPEECH_REGION=australiaeast
FOUNDRY_MODEL=gpt-4o-mini

# Scripts 6, 7 — Azure OpenAI Speech resource
AZURE_OPENAI_SPEECH_ENDPOINT=https://<openai-resource>.cognitiveservices.azure.com
AZURE_OPENAI_SPEECH_KEY=<openai-speech-key>

# Script 8 — Azure AI Services (Voice Live)
VOICELIVE_ENDPOINT=https://<ai-services-resource>.cognitiveservices.azure.com
VOICELIVE_KEY=<ai-services-key>
VOICELIVE_MODEL=gpt-5.3-chat
```

> Script 1 (`1_SpeechSynthesis.py`) has its key hardcoded at the top of the file — update `SPEECH_KEY` and `SPEECH_REGION` directly in that file before class.

---

## Neural Voices Used (no deployment needed — built-in)

These voices are used via the Speech SDK and require no separate provisioning:

| Voice name | Used in |
|---|---|
| `en-US-AriaNeural` | Script 1 (TTS) |
| `en-AU-WilliamNeural` | `create_demo_audio.py` (Doctor) |
| `en-AU-NatashaNeural` | `create_demo_audio.py` (Patient) |
| `ja-JP-NanamiNeural` | Script 5 (Japanese) |
| `fr-FR-DeniseNeural` | Script 5 (French) |
| `es-ES-ElviraNeural` | Script 5 (Spanish) |
| `hi-IN-SwaraNeural` | Script 5 (Hindi) |
| `zh-CN-XiaoxiaoNeural` | Script 5 (Chinese) |
| `en-US-AvaNeural` | Script 8 (Voice Live agent) |
| `alloy` | Scripts 6, 7 (Azure OpenAI TTS voice) |

---

## CLU Projects (Session 1) — What the Trainer Scripts Do

Scripts 1 and 2 in Session 1 create, train, and deploy CLU projects **automatically via the API**. The TA does not need to set these up in the portal. However, be aware:

| Script | CLU Project Created | Intents | Entities |
|---|---|---|---|
| `1_CLU_Trainer_Menu.py` | `Menu` | `Send` | `Contact` (Person.Name prebuilt) |
| `2_CLU_Trainer_GetTimeAndSend.py` | `GetTimeAndSend` | `GetTime`, `Send` | `Location`, `Contact` |

- Training can take **2–5 minutes** per project — run these before class or during setup time.
- The trained model label is `Sample5` in both scripts.
- The deployment target is `production` in both scripts.
- If re-running, the scripts will overwrite the existing project with the same name.

---

## Pre-Class Checklist

### Session 1
- [ ] Azure AI Language Service resource created (Standard tier)
- [ ] Endpoint and key copied and ready to paste into scripts
- [ ] Run `1_CLU_Trainer_Menu.py` to pre-train the Menu CLU project
- [ ] Run `2_CLU_Trainer_GetTimeAndSend.py` to pre-train the GetTimeAndSend CLU project
- [ ] Verify scripts 3 and 4 work (CLU client queries)
- [ ] Verify scripts 5–11 work (Text Analytics)

### Session 2
- [ ] Azure AI Foundry hub + project created in `australiaeast`
- [ ] `gpt-4o-mini` deployed in Foundry project
- [ ] Foundry key, endpoint, and region noted
- [ ] Azure OpenAI resource created in a region with audio model support (e.g. `eastus`)
- [ ] `gpt-4o-mini-tts` deployed in Azure OpenAI
- [ ] `gpt-4o-mini-transcribe` deployed in Azure OpenAI
- [ ] Azure AI Services (multi-service) resource created for Voice Live
- [ ] `.env` file filled in with all values and tested
- [ ] Run scripts 1–8 end-to-end at least once before class
- [ ] `audio/consultation.wav` exists (run `create_demo_audio.py` if not)
- [ ] Microphone permissions granted to the terminal / VS Code
- [ ] Speakers working and volume audible to the room

---

## Regional Availability Notes

| Model | Confirmed Regions |
|---|---|
| `gpt-4o-mini` | Most regions including `australiaeast`, `eastus` |
| `gpt-4o-mini-tts` | `eastus`, `swedencentral` (limited — verify before class) |
| `gpt-4o-mini-transcribe` | `eastus`, `swedencentral` (limited — verify before class) |
| Voice Live (`gpt-5.3-chat`) | `eastus` (preview — verify availability before class) |

> Always check the [Azure AI model availability page](https://learn.microsoft.com/azure/ai-services/openai/concepts/models) the day before class, as preview models can be added to or removed from regions.
