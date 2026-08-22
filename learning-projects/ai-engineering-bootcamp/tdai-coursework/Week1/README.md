# Week 1: LLM Fundamentals - Exercises

This folder contains hands-on Python exercises for the following foundational topics in AI engineering:

## Topics Covered
- Running a Local LLM (LM Studio)
- LLM Output & Autocomplete behaviour
- Hallucination
- Tokenization
- Vectorization
- Attention
- Few-Shot Prompting
- Retrieval-Augmented Generation (RAG)
- Vector Database Search

## Setup

This folder has its own `.env` file. Copy the example and fill in your values before running any Azure-dependent scripts:

```powershell
copy .env.example .env
```

Then open `.env` and set your Azure endpoint, deployment name, and API key. The `.env.example` file documents every variable and which exercise uses it.

## How to Run Each Exercise

Run all scripts from inside the `Week1` folder so they pick up the local `.env`:

```powershell
cd Week1
python ex0_local_llm.py
python ex1_llm_output.py
python ex2_hallucination.py
python ex3_tokenization.py
python ex4_vectorization.py
python ex5_attention.py
python ex6_few_shot.py
python ex7_rag.py
python ex8_vector_db.py
```

- **ex0** requires LM Studio to be installed and running locally with a model loaded (no Azure needed).
- **ex1, ex2, ex4, ex5, ex6, ex7** require your `.env` file to be configured with your Azure endpoint, deployment name, and API key. The current deployment is `gpt-4.1-mini`.
- **ex3 and ex8** need no API key — they run entirely locally.

## What You'll Learn
- How to run an LLM locally on your own machine without any cloud API
- How LLMs work as autocomplete engines
- How LLMs can hallucinate (make up facts) — note: newer models like `gpt-4.1-mini` are better at refusing to fabricate, which is itself a useful teaching point
- How text is split into tokens
- How to get and compare vector embeddings
- How LLMs use attention to resolve ambiguity
- How to guide models with few-shot examples
- How to ground answers in private data (RAG)
- How to use a vector database for semantic search

---

Explore, experiment, and have fun learning the building blocks of modern AI systems!
