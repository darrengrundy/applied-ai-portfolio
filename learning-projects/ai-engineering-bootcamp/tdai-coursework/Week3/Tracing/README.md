# OpenTelemetry Tracing with Azure OpenAI

This example demonstrates how to trace Azure OpenAI API calls using OpenTelemetry and export the results to Azure Application Insights.

## How it works

```
Your prompt
     ↓
OpenAI API call  (instrumented by OpenAIInstrumentor)
     ↓
Span captured   → Console (immediate output)
                → Application Insights (visible in Azure portal)
```

Each span contains: model name, prompt, response, token usage, latency, and content filter results.

---

## Prerequisites

```bash
pip install openai opentelemetry-sdk opentelemetry-instrumentation-openai azure-monitor-opentelemetry-exporter python-dotenv
```

---

## Setup

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

| Variable | Where to find it |
|---|---|
| `ENDPOINT_URL` | Azure Portal → Your OpenAI resource → Keys and Endpoint |
| `AZURE_OPENAI_API_KEY` | Azure Portal → Your OpenAI resource → Keys and Endpoint |
| `API_VERSION` | Use `2025-01-01-preview` |
| `DEPLOYMENT_NAME_GPT_4_mini` | Azure AI Foundry → Deployments → your model name |
| `TRACE_CONNECTION_STRING` | Azure Portal → Application Insights → Overview → Connection String |

---

## Run

```bash
python trace_test.py
```

You will see the full span printed to the console, followed by the model response.

---

## Viewing traces in Azure Portal

1. Go to **Azure Portal → Application Insights → your resource**
2. Under **Investigate** → click **Transaction search**
3. Traces appear within **1–2 minutes** of running the script
4. Click any result to see the full span details: prompt, response, token counts, latency

---

## What you will learn

- How OpenTelemetry **TracerProvider** and **SpanProcessor** work
- How to use `OpenAIInstrumentor` to automatically capture LLM call spans
- How to export traces to **Azure Application Insights** using `AzureMonitorTraceExporter`
- What a trace span looks like — model, tokens, prompt, response, content filters
