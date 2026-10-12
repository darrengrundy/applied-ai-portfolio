# Microsoft AI Engineering (AI-103)

This tracker covers the **30 practical exercises** retained for Microsoft course AI-103, grouped into four learning areas, plus a short list of optional extras. It tracks three separate things: whether the lab has been **run hands-on**, whether there is publishable **portfolio evidence**, and how the lab is being **adapted to a transport and supply-chain scenario**. None of these columns represents formal course or exam completion.

The exercise names and numbering follow the local AI-103 course pack retained in August 2026. Microsoft updates its live exercise catalogues over time, so the linked catalogues may not always contain the same historical set or wording.

## How labs are run

- **Subscription:** labs are run in my personal pay-as-you-go Azure subscription (`AI-103-labs`), separate from any employer or course tenant. Earlier DAX work was run on the course subscription.
- **Portal first, then code:** the early labs are completed in the Microsoft Foundry portal; later labs use VS Code with the Python SDKs and `DefaultAzureCredential` (Azure CLI sign-in), consistent with the rest of this repository.
- **One folder per lab:** each completed lab gets its own folder in this directory, named `<number>-<short-name>` (for example `1-2-explore-compare-models/`), scaffolded from [`templates/PROJECT_README_TEMPLATE.md`](../../templates/PROJECT_README_TEMPLATE.md). Shared DAX labs link to the existing DAX project instead of duplicating it.
- **Clean-up:** each lab's resource group is deleted when the lab is finished, unless a later lab reuses it.
- **Security:** `.env` files, keys, endpoints, tenant IDs and email addresses are never committed; screenshots are scrubbed before publishing.

## Status key

**Lab run** - the date the Microsoft lab was completed hands-on. Blank means not yet run. This column is independent of portfolio status: a lab can be run without producing a portfolio project, and a shared DAX project can exist for a lab I have not personally sat.

**Portfolio status**

- **Shared evidence - DAX #n:** the same Microsoft exercise is already represented by a DAX assignment; one project page supports both learning tracks.
- **Validation blocked - DAX #n:** the DAX implementation exists and is linked, but it was never validated against Azure because of a platform blocker on the DAX subscription. The linked project page carries the precise state of the code. These will be re-run in my own Azure subscription as they come up in the 1-30 sequence, and re-tagged then.
- **Related work - verify:** relevant local code or outputs exist, but they still need to be checked against the exact AI-103 exercise requirements.
- **Planned - shared with DAX #n:** the exercise also appears on the DAX assignment list but has not yet been completed.
- **Planned:** no verified portfolio evidence yet.

**Supply-chain adaptation** - the planned transport or logistics twist applied after the standard lab steps are complete. These are intentions, not claims; a project page only describes an adaptation once it has been built and tested.

## 1. Develop generative AI apps in Azure

[Microsoft exercise catalogue](https://microsoftlearning.github.io/mslearn-ai-studio/)

| # | Exercise | Lab run | Portfolio status | Supply-chain adaptation |
|---:|---|---|---|---|
| 1.1 | [Plan and prepare to develop AI solutions on Azure](https://microsoftlearning.github.io/mslearn-ai-studio/Instructions/Exercises/01-Explore-ai-studio.html) | 2026-09-06 (re-run planned in AI-103-labs) | [Shared evidence - DAX #1](../ai-engineering-bootcamp/01-foundry-project-setup/) | Foundry project set up as the shared base for all later labs |
| 1.2 | [Select, deploy, and evaluate Microsoft Foundry models](https://microsoftlearning.github.io/mslearn-ai-studio/Instructions/Exercises/02-model-catalog-evaluation.html) | | Related work - verify | Compare models on carrier email triage and freight-rate questions |
| 1.3 | [Develop a generative AI chat app with Microsoft Foundry](https://microsoftlearning.github.io/mslearn-ai-studio/Instructions/Exercises/03-foundry-sdk.html) | | [Validation blocked - DAX #2](../ai-engineering-bootcamp/02-generative-ai-chat-app/) | Transport operations assistant answering dispatch and booking questions |
| 1.4 | [Develop generative AI apps that use tools](https://microsoftlearning.github.io/mslearn-ai-studio/Instructions/Exercises/04a-use-own-data.html) | | [Validation blocked - DAX #3](../ai-engineering-bootcamp/03-generative-ai-tools-app/) | Tools for freight-cost lookup and delivery ETA calculation |
| 1.5 | [Optimize generative AI model performance with Microsoft Foundry](https://microsoftlearning.github.io/mslearn-ai-studio/Instructions/Exercises/04b-finetune-model.html) | | Planned | Fine-tune on synthetic carrier-communication examples for a consistent tone |
| 1.6 | [Implement a responsible generative AI solution in Microsoft Foundry](https://microsoftlearning.github.io/mslearn-ai-studio/Instructions/Exercises/06-Explore-content-filters.html) | | [Shared evidence - DAX #6](../ai-engineering-bootcamp/06-responsible-ai-guardrails/) | Guardrails for a driver-facing assistant (safety and fatigue topics) |

## 2. Develop AI agents on Azure

[Microsoft exercise catalogue](https://microsoftlearning.github.io/mslearn-ai-agents/)

| # | Exercise | Lab run | Portfolio status | Supply-chain adaptation |
|---:|---|---|---|---|
| 2.1 | [Develop AI agents with Microsoft Foundry and Visual Studio Code](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/01-build-agent-portal-and-vscode.html) | | [Validation blocked - DAX #4](../ai-engineering-bootcamp/04-ai-agent/) | Delivery exception agent built in the portal and extended in VS Code |
| 2.2 | [Integrate custom tools into your agent](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/02-agent-custom-tools.html) | | Related work - verify | Custom function scoring carrier on-time performance from a CSV |
| 2.3 | [Integrate MCP tools with Azure AI Agents](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/03-mcp-integration.html) | | Related work - verify | MCP server exposing a mock consignment-tracking API |
| 2.4 | [Build knowledge-enhanced AI agents with Foundry IQ](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/04-integrate-agent-with-foundry-iq.html) | | Planned - shared with DAX #9 | Agent grounded on Chain of Responsibility (CoR) guidance documents |
| 2.5 | [Integrate your agent with Microsoft 365](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/05a-m365-teams-integration.html) | | Planned | Transport-desk agent published to Teams |
| 2.6 | [Build agent-driven workflows using Microsoft Foundry](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/06-build-workflow-ms-foundry.html) | | Planned - shared with DAX #10 | Freight-invoice approval workflow with a human approval step |
| 2.7 | [Develop an AI agent with Microsoft Agent Framework](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/07-agent-framework.html) | | Planned | Carrier performance agent built with the Agent Framework SDK |
| 2.8 | [Orchestrate a multi-agent solution using Microsoft Agent Framework](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/08-agent-framework-multi-agents.html) | | Related work - verify | Builds on the [CoR multi-agent prototype](../../my-lane-projects/transport-cor-multi-agent/) |
| 2.9 | [Discover Azure AI Agents with A2A](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/09-multi-remote-agents-with-a2a.html) | | Planned | Shipper agent negotiating a booking with a remote carrier agent |

## 3. Develop natural language solutions in Azure

[Microsoft exercise catalogue](https://microsoftlearning.github.io/mslearn-ai-language/)

| # | Exercise | Lab run | Portfolio status | Supply-chain adaptation |
|---:|---|---|---|---|
| 3.1 | [Analyze text with Azure Language in Foundry Tools](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/01-analyze-text.html) | | Related work - verify | Sentiment and entity extraction on customer delivery feedback |
| 3.2 | [Develop a text analysis agent with the Azure Language MCP server](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/02-language-agent.html) | | Planned | Agent that triages incoming carrier and customer emails |
| 3.3 | [Develop a speech-capable generative AI application](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/03-gen-ai-speech.html) | | Related work - verify | Voice notes from drivers summarised into incident reports |
| 3.4 | [Create speech-enabled apps with Azure Speech in Microsoft Foundry Tools](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/04-azure-speech.html) | | Related work - verify | Spoken delivery status read-outs for warehouse staff |
| 3.5 | [Develop a speech agent with the Azure Speech MCP server](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/05-azure-speech-mcp.html) | | Planned | Hands-free speech agent for drivers to log delays |
| 3.6 | [Develop an Azure Speech Voice Live Agent in Microsoft Foundry](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/06-voice-live-agent.html) | | Planned | Real-time voice dispatch assistant |
| 3.7 | [Translate text and speech with Microsoft Foundry Tools](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/07-translation.html) | | [Shared evidence - DAX #8](../ai-engineering-bootcamp/08-translate-text-and-speech/) | Translated safety briefings for a multilingual driver workforce |

## 4. Extract insights from visual data on Azure

[Microsoft exercise catalogue](https://microsoftlearning.github.io/mslearn-ai-vision/)

| # | Exercise | Lab run | Portfolio status | Supply-chain adaptation |
|---:|---|---|---|---|
| 4.1 | [Develop a vision-enabled generative AI application](https://microsoftlearning.github.io/mslearn-ai-vision/Instructions/Exercises/01-gen-ai-vision.html) | | Planned | Load photos checked for damage and unsafe load restraint |
| 4.2 | [Generate images with AI](https://microsoftlearning.github.io/mslearn-ai-vision/Instructions/Exercises/02-generate-image.html) | | [Shared evidence - DAX #7](../ai-engineering-bootcamp/07-generate-images-with-ai/) | Visual safety signage and training illustrations |
| 4.3 | [Generate videos with Microsoft Foundry](https://microsoftlearning.github.io/mslearn-ai-vision/Instructions/Exercises/03-generate-video.html) | | Planned | Short safety-induction clip (watch the cost of video generation) |
| 4.4 | [Analyze images with Content Understanding](https://microsoftlearning.github.io/mslearn-ai-vision/Instructions/Exercises/04-content-understanding.html) | | Planned | Proof-of-delivery photo analysis |
| 4.5 | [Create a multimodal analysis solution with Azure Content Understanding](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/01-content-understanding.html) | | Planned | Consignment notes, PODs and delivery photos analysed together |
| 4.6 | [Create an Azure Content Understanding client application](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/02-content-understanding-api.html) | | Related work - verify | Client app extracting fields from carrier documents |
| 4.7 | [Extract data with Azure Document Intelligence](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/03-document-intelligence.html) | | Related work - verify | Freight-invoice extraction for cost auditing |
| 4.8 | [Create a knowledge-mining solution with Azure AI Search](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/04-knowledge-mining.html) | | Related work - verify | Searchable archive of carrier contracts and rate cards |

## Optional extras

These are outside the 30 retained exercises but are listed in the current AI-103 lab guide.

| Exercise | Type | Lab run | Status | Supply-chain adaptation |
|---|---|---|---|---|
| [Build an automated RAG ingestion pipeline with Content Understanding](https://microsoftlearning.github.io/mslearn-ai-information-extraction/Instructions/Exercises/05-rag-pipeline.html) | Extension (follows 4.5-4.7) | | Planned | Freight invoices and PODs ingested into a searchable knowledge base |
| [Work IQ - workplace intelligence for AI agents](https://microsoftlearning.github.io/mslearn-ai-agents/Instructions/Exercises/05b-work-iq-integration.html) | Optional (follows 2.5) | | Optional - needs Microsoft 365 licensing | |
| Azure AI Services foundations: [get started](https://microsoftlearning.github.io/mslearn-ai-services/Instructions/Labs/01-use-azure-ai-services.html), [security](https://microsoftlearning.github.io/mslearn-ai-services/Instructions/Labs/02-ai-services-security.html), [monitoring](https://microsoftlearning.github.io/mslearn-ai-services/Instructions/Labs/03-monitor-ai-services.html), [containers](https://microsoftlearning.github.io/mslearn-ai-services/Instructions/Labs/04-use-a-container.html), [content safety](https://microsoftlearning.github.io/mslearn-ai-services/Instructions/Labs/05-implement-content-safety.html) | Prerequisites | | Optional - largely covered by DAX Weeks 5-8 | |

## Publishing approach

We will audit one exercise at a time against its instructions, locate the retained code and screenshots, and then either link an existing project page or publish a concise new one using the repository template. Shared DAX/AI-103 exercises remain one implementation with two curriculum references; they are not counted as two separate technical projects.
