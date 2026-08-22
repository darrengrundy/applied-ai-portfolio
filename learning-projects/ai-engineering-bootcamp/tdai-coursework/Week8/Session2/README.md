# Week 8 Session 2 — Azure AI Search & Multi-Agent Solutions

Hands-on demos covering knowledge mining with Azure AI Search, MCP tool integration, and multi-agent pipelines using the Azure AI Foundry Responses API.

## Scripts

| Script | What it demonstrates |
|--------|----------------------|
| `1_SearchIndex_TravelBrochures.py` | Queries an Azure AI Search index built from PDFs using an indexer with cognitive skills (NER, key phrase extraction). Runs a live search loop. |
| `2_SemanticSearch.py` | Advanced query modes: BM25 full-text, field-scoped search, AI semantic ranking (with graceful fallback), and faceted aggregations. |
| `3_MCP_RemoteServer.py` | Agent loop that connects to Microsoft Learn's public MCP server and uses it to answer Azure documentation questions. |
| `inventory_server.py` | FastMCP server exposing 2 inventory tools over stdio — `get_inventory_levels` and `get_weekly_sales`. |
| `4_MCP_CustomInventory.py` | Agent loop that starts `inventory_server.py` as a subprocess and answers any inventory question via the chat prompt. |
| `5_MultiAgent_BlogPost.py` | Orchestrated pipeline using the Foundry Responses API: Title Agent → Outline Agent, each with a focused system prompt. |

## Prerequisites

- Python 3.11 or later
- An **Azure AI Search** resource
  - Free tier (F0) works for scripts 1 and 2
  - Semantic search in script 2 requires Basic tier or above
  - Scripts 1 and 2 require an indexer with cognitive skills set up (see below)
- An **Azure AI Foundry** project with a deployed chat model (for scripts 3, 4, 5)
  - Recommended model: `gpt-4o-mini`

## Setup

### 1. Get the repo

```bash
git pull
cd Week8/Session2
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
pip install azure-search-documents azure-ai-textanalytics azure-core openai mcp python-dotenv httpx requests pypdf
```

### 4. Configure credentials

```bash
# Windows
copy .env.example .env

# macOS / Linux
cp .env.example .env
```

Open `.env` and fill in your values:

```
# Azure AI Search
SEARCH_ENDPOINT=https://<your-search-name>.search.windows.net
QUERY_KEY=<your-query-key>
ADMIN_KEY=<your-admin-key>
INDEX_NAME=<your-index-name>
LANGUAGE_KEY=<your-language-or-foundry-key>
LANGUAGE_ENDPOINT=https://<your-language-resource>.cognitiveservices.azure.com/

# Azure AI Foundry project
AZURE_AI_ENDPOINT=https://<resource>.cognitiveservices.azure.com/openai/v1
AZURE_AI_KEY=<your-key>
AZURE_AI_MODEL=gpt-4o-mini
```

Where to find these:
- **Azure Portal** → your AI Search resource → **Keys and Endpoint** (Query key and Admin key are listed separately)
- **Azure Portal** → your AI Language resource → **Keys and Endpoint**
- **Azure AI Foundry** → your resource → **Keys and Endpoint** → your deployed model key

### 5. Populate the AI Search index (scripts 1 & 2)

Run the one-time setup script. It reads the PDFs from `documents/`, extracts text, runs Azure AI Language for NER and key phrases, then pushes all 6 documents to the index:

```bash
python setup_search_index.py
```

This takes about 30 seconds and creates the index automatically. No blob storage or portal setup required.

## Running the Demos

```bash
# Demo 1 — Knowledge mining: search the indexed travel brochures
python 1_SearchIndex_TravelBrochures.py

# Demo 2 — Advanced queries: full-text, field-scoped, semantic, facets
python 2_SemanticSearch.py

# Demo 3 — Agent + Microsoft Learn remote MCP server
python 3_MCP_RemoteServer.py

# Demo 4 — Agent + custom inventory MCP server (interactive chat)
python 4_MCP_CustomInventory.py

# Demo 5 — Multi-agent blog post pipeline
python 5_MultiAgent_BlogPost.py
```

## Expected Output

### Demo 1 — Knowledge Mining

```
Enter a query (or type 'quit' to exit): New York

Search returned 1 documents:

Document: New York Brochure.pdf
 - Locations:
   - New York
   - Manhattan
   - Central Park
 - People:
   - (none)
 - Key phrases:
   - world-class dining
   - Times Square
   - Broadway shows
```

### Demo 2 — Advanced Queries

```
  Query 1 — Full-text: 'beach'
  [2.31]  Dubai Brochure.pdf
    Locations : Dubai, Persian Gulf
    Keyphrases: luxury beach resorts, desert safaris

  Query 3 — Semantic: 'famous landmarks and tourist attractions'
  Semantic search unavailable on this tier — falling back to full-text...
```

### Demo 3 — Remote MCP Agent

```
  Tools available from MS Learn MCP: 3
    - microsoft_docs_search
    - microsoft_code_sample_search
    - microsoft_docs_fetch

  [Iteration 1] Calling LLM...
  [Tool call] microsoft_docs_search
    args: {"query": "Azure AI Search pricing tiers"}
    Approved - executing via MCP...

  AGENT ANSWER:
  Azure AI Search has four pricing tiers: Free, Basic, Standard (S1/S2/S3),
  and Storage Optimised. The Free tier supports up to 3 indexes and 50 MB...
```

### Demo 4 — Custom MCP Agent

```
  MCP server connected. Tools available: 2
    - get_inventory_levels
    - get_weekly_sales

USER: Which products are running low?

  [Tool] get_inventory_levels()
  [Result] {"Moisturizer": 6, "Shampoo": 8, ...}

ASSISTANT: Based on current stock levels, Hair Gel (5 units) and
Conditioner (3 units) are running lowest. Shampoo (8) and
Moisturizer (6) are also getting low given last week's sales...
```

### Demo 5 — Multi-Agent Pipeline

```
  [Title Agent] Generating headlines...

  1. Build a Real-Time Inventory Agent with Azure MCP in 30 Minutes
  2. From Static Python to AI Agent: The MCP Transformation
  3. How We Cut Manual Stock Reviews by 90% with Custom MCP Tools

  [Outline Agent] Structuring: 'Build a Real-Time Inventory Agent...'

  Introduction
    In this tutorial you will build a production-ready AI agent...

  Section 1: What is MCP and Why It Matters
    ...
```

## Key Concepts

### Knowledge Mining (Scripts 1 & 2)

`setup_search_index.py` builds the index programmatically:
1. Reads the 6 PDFs from `documents/` using `pypdf`
2. Calls **Azure AI Language** to extract locations, people, and key phrases (NER + key phrase extraction)
3. Pushes the enriched documents to the Azure AI Search index with a semantic configuration

Once indexed, content from inside unstructured PDFs becomes queryable via full-text, field-scoped, semantic, and faceted queries.

### MCP Integration (Scripts 3 & 4)

**Model Context Protocol (MCP)** is an open standard that lets AI agents discover and invoke tools at runtime.

| | Remote MCP (Script 3) | Custom MCP (Script 4) |
|---|---|---|
| Server | Microsoft Learn (`learn.microsoft.com/api/mcp`) | Your own `inventory_server.py` |
| Transport | Streamable HTTP | stdio (subprocess) |
| Use case | Public documentation | Private business data |

### Multi-Agent Orchestration (Script 5)

Each agent is created with a focused `instructions` prompt via the Foundry Responses API. The orchestrator routes the output of one agent as the input to the next — no agent does more than one job.

```
Orchestrator
    |
    +--> Title Agent    -> 3 headline options
    |         |
    |    [chosen title]
    |         |
    +--> Outline Agent  -> full article structure
```

## Resources

- [Azure AI Search documentation](https://learn.microsoft.com/azure/search/)
- [Azure AI Foundry documentation](https://learn.microsoft.com/azure/ai-foundry/)
- [Model Context Protocol specification](https://modelcontextprotocol.io)
- [MCP integration lab](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/03-mcp-integration.html)
- [Knowledge Mining lab](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/04-knowledge-mining.html)
