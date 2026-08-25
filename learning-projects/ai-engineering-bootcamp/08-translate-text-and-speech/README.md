# Translate Text and Speech

> Shared portfolio evidence for **DAX AI Engineering Bootcamp Assignment 8** and **Microsoft AI-103 Exercise 3.7**.

## Overview

This project demonstrates real-time text and speech translation using Azure AI services through Microsoft Foundry. Two Python clients are implemented: one that translates typed text from any language to a chosen target language using Azure Translator with automatic source-language detection, and one that captures spoken English from a microphone, translates it to multiple target languages simultaneously, and synthesises the results as spoken audio using Azure AI Speech neural voices.

The exercise was validated live on 25 August 2026. No API key is stored in the project.

## Result

Both clients ran successfully. The speech translation client captured microphone input, recognised the English utterance, and returned translations in French, Spanish, and Hindi with correct date localisation in each language.

### Terminal output — speech translation

```
Speak now...
Translating 'Testing 1-2 Test test, test. This is from my laptop on the 25th of August 2026.'
fr: 'Test 1-2 Test test, test. C'est depuis mon ordinateur portable du 25 août 2026.'
es: 'Prueba 1-2 Prueba, prueba. Esto es de mi portátil del 25 de agosto de 2026.'
hi: 'परीक्षण 1-2 परीक्षण परीक्षण, परीक्षण. यह 25 अगस्त 2026 को मेरे लैपटॉप से है।'
```

## Solution flow

```mermaid
flowchart LR
    A["Text input / microphone"] --> B["Python client"]
        B --> C1["Azure Translator\n(text translation)"]
            B --> C2["Azure AI Speech SDK\nTranslationRecognizer\n(speech translation)"]
                C1 --> D1["Translated text\nin target language"]
                    C2 --> D2["SpeechConfig\nneural voice synthesis"]
                        D2 --> E["Audio output\nthrough speaker"]
                        ```

                        ## Azure configuration

                        | Item | Value |
                        |---|---|
                        | Foundry project | `darren-3490` |
                        | Resource | `darren-3490-resource` |
                        | Services | Azure AI Speech + Azure Translator |
                        | Authentication | Token credential via Microsoft Foundry endpoint |
                        | Speech translation target languages | French (`fr`), Spanish (`es`), Hindi (`hi`) |
                        | Neural voices | `fr-FR-HenriNeural`, `es-ES-ElviraNeural`, `hi-IN-MadhurNeural` |

                        ## Run locally

                        ### Prerequisites

                        - Python 3.13
                        - Azure AI Speech SDK (`azure-cognitiveservices-speech`)
                        - Access to the Azure subscription containing the Speech and Translator deployments
                        - A working microphone (for speech translation)

                        ### Setup

                        1. Create and activate a virtual environment:

                           ```powershell
                              python -m venv .venv
                                 .venv\Scripts\Activate.ps1
                                    ```

                                    2. Install the dependencies:

                                       ```powershell
                                          pip install -r requirements.txt
                                             ```

                                             3. Copy `.env.example` to `.env` and populate the Foundry endpoint and token credential values.

                                             4. Run the text translation client:

                                                ```powershell
                                                   python translate-text.py
                                                      ```

                                                      5. Run the speech translation client (microphone required):

                                                         ```powershell
                                                            python translate-speech.py
                                                               ```

                                                               ## Security

                                                               - The portfolio contains `.env.example` with placeholders only.
                                                               - The working `.env` file is not included.
                                                               - No API key, subscription key, or tenant ID is published.
                                                               - Runtime authentication uses the Foundry token credential via `DefaultAzureCredential`.

                                                               ## Lessons learned

                                                               - The `TranslationRecognizer` class in the Azure Speech SDK handles speech recognition and translation in a single pass — no separate recognition step is needed.
                                                               - Neural voice synthesis for translated output requires a separate `SpeechConfig` targeting the synthesis language; translation config and synthesis config are distinct SDK objects.
                                                               - Language codes for translation targets (`fr`, `es`, `hi`) differ from voice locale codes (`fr-FR`, `es-ES`, `hi-IN`), so both must be configured independently.
                                                               - Azure Translator performs automatic source-language detection, so the text client does not need the user to specify the input language.
                                                               - Azure Translator Text and Azure AI Speech are separate services with separate endpoints and credential configurations, even when both are accessed through the same Foundry resource.

                                                               ## Limitations and next steps

                                                               - The speech client uses `recognize_once_async`, which captures a single utterance; a production implementation would use continuous recognition.
                                                               - Error handling for no-speech or cancelled results is minimal in the lab version.
                                                               - Future work could add streaming translation, additional target languages, output to audio files, and a lightweight web interface.

                                                               ## Attribution

                                                               Adapted from Microsoft Learning's [Translate text and speech](https://microsoftlearning.github.io/mslearn-ai-language/Instructions/Exercises/07-translation.html) exercise and the [`mslearn-ai-language`](https://github.com/MicrosoftLearning/mslearn-ai-language) starter repository. The Azure setup, completed code sections, translation outputs, troubleshooting notes, and portfolio documentation are the learner's work.
