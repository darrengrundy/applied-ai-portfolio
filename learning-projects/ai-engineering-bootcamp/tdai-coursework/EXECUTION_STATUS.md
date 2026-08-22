# Execution status

Validation was completed in Visual Studio Code on Windows using a shared Python virtual environment. The final audit was completed on **22 August 2026**.

## Results by week

| Week | Result | Evidence and limitations |
|---|---|---|
| 1 | 10/10 passed | Local LM Studio, Azure OpenAI, hallucination, tokenization, vectorization, attention, few-shot, RAG, vector database and REST examples were exercised. |
| 2 | 8/8 accounted for | Function-agent and data-analysis demonstrations ran. The active Foundry implementations completed; two retained classic/archive paths are reference implementations for superseded APIs. |
| 3 | 4/4 passed | Prompt Flow chat, Wikipedia retrieval helpers and Application Insights tracing were exercised. A deprecation warning recommends `promptflow.core.tool` for future maintenance. |
| 4 | Not applicable | The course schedule specifies no Week 4 assignment. |
| 5 | 8/8 passed | Content Safety, blocklist management, PII/profanity examples, Semantic Kernel helpers and the Jupyter notebook ran successfully. |
| 6 | 7/7 accounted for | Current Vision/OCR/image-analysis examples passed. Two Custom Vision examples depend on a retired or unavailable legacy endpoint and are retained as migration evidence rather than represented as live successes. |
| 7 | 20/20 accounted for | All active Language and Speech scripts passed, including speech synthesis, microphone recognition, translation, GPT audio generation and transcription. Seven archive scripts are retained as historical/reference implementations. |
| 8 | 13/13 accounted for | Ten runnable demos and read-only utilities passed. `inventory_server.py` was exercised through its parent MCP demo. The two one-time provisioning utilities were reviewed but not rerun because they mutate shared Azure Search resources. |

## Representative successful outputs

- grounded RAG answers with cited context;
- a Foundry code-interpreter analysis and saved chart;
- a traced model response and a working Prompt Flow wiki chat;
- Content Safety classifications and a complete temporary blocklist lifecycle;
- OCR, object, landmark and brand/tag analysis;
- language detection, NER, sentiment and extractive summarisation;
- text-to-speech, speech-to-text and live English-to-Japanese translation;
- invoice extraction, semantic search facets, remote/custom MCP calls and a multi-agent blog outline.

## Meaning of "accounted for"

"Passed" means the demonstration produced its expected local or Azure-backed result during the audit. "Accounted for" also permits a clearly identified helper, archive, provisioning script or externally constrained legacy example. This avoids both unsafe cloud mutations and misleading claims that obsolete dependencies are current production code.

## Maintenance notes

- Azure services and SDKs evolve quickly; deprecation warnings are retained where they teach a useful migration lesson.
- A fresh user must provide their own Azure resources, deployments, quotas and credentials.
- Setup/provisioning scripts should be reviewed before execution because they can create, replace or delete shared cloud resources.
