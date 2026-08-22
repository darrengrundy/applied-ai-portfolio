# Chat With Wikipedia

This flow builds a RAG-style chatbot that searches Wikipedia in real time to answer your questions — grounding every response in actual sources rather than model memory alone.

## How it works

Each message goes through a 5-step pipeline:

```
Your question
     ↓
1. extract_query_from_question  →  pulls out the search term (uses GPT)
     ↓
2. get_wiki_url                 →  finds matching Wikipedia article URLs
     ↓
3. search_result_from_url       →  fetches the article text (parallel)
     ↓
4. process_search_result        →  formats content as context
     ↓
5. augmented_chat               →  generates a grounded answer with SOURCES
```

---

## Prerequisites

Install dependencies:

```bash
pip install -r requirements.txt
```

---

## Setup — Create the Azure OpenAI connection

The flow uses a named connection called `azure_open_ai_connection`. You only need to do this once.

1. Open `azure_openai.yml` (in this folder) and fill in your values:

```yaml
api_key: "<provided by trainer>"
api_base: "https://<your-foundry-resource>.openai.azure.com/"
```

2. Register the connection:

```bash
cd Week3/chat-wiki
pf connection create --file azure_openai.yml
```

Verify it was saved:

```bash
pf connection show --name azure_open_ai_connection
```

> If you need to update it later:
> ```bash
> pf connection update -n azure_open_ai_connection \
>   --set api_key=<your_api_key> \
>          api_base=<your_azure_openai_endpoint>
> ```

---

## Testing the flow

Run all commands from the `Week3/chat-wiki/` folder.

### Option 1 — Single question (quick test)

```bash
pf flow test --flow . --inputs question="What is the Turing Test?" chat_history="[]"
```

### Option 2 — Interactive chat in the terminal

Maintains conversation history automatically. Type your questions one by one:

```bash
pf flow test --flow . --interactive
```

### Option 3 — Visual UI in the browser (recommended for demos)

Opens a local chat interface that also shows each node's execution trace:

```bash
pf flow test --flow . --ui
```

### Option 4 — Batch test against sample data

Runs all test cases in `data.jsonl` and streams results:

```bash
pf run create --flow . --data data.jsonl --stream
```

---

## Sample questions to try

The flow works best with factual, knowledge-based questions. Here are some to get you started:

**AI & Technology**
- `What is GPT-4 and how does it differ from GPT-3?`
- `How does reinforcement learning work?`
- `What is the difference between supervised and unsupervised learning?`
- `What is a transformer model in machine learning?`

**Science & History**
- `Who invented the World Wide Web and how does it work?`
- `What caused the 2008 financial crisis?`
- `How does CRISPR gene editing work?`
- `What is quantum entanglement?`

**Multi-turn conversation (try these in sequence in `--interactive` mode)**
1. `What is the Python programming language?`
2. `Who created it and when?`
3. `What are its main use cases today?`
4. `How does it compare to JavaScript?`

> The flow uses conversation history so follow-up questions like "Who created it?" will correctly refer back to what was just discussed.

---

## What you will learn

- How to compose a multi-step **chat flow** in Prompt Flow
- How to pass and consume **chat history** across turns:
    ```jinja
    {% for item in chat_history %}
    # user:
    {{item.inputs.question}}
    # assistant:
    {{item.outputs.answer}}
    {% endfor %}
    ```
- How to write **Jinja2 prompt templates** for LLM nodes
- How to build **parallel web scraping** with `ThreadPoolExecutor`
- How to chain Python tools and LLM nodes in a DAG pipeline
- How to ground model responses in **retrieved sources** (RAG pattern)
