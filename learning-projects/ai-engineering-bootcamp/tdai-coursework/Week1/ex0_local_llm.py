"""
Exercise: Running a Local LLM with LM Studio
=============================================
Instead of sending prompts to a cloud API, you can run an LLM entirely
on your own machine using LM Studio (https://lmstudio.ai).

LM Studio exposes an OpenAI-compatible server, so we can use the same
`openai` Python library — just pointed at localhost instead of Azure.

Setup:
  1. Download and open LM Studio.
  2. Download a model (e.g. liquid/lfm2.5-1.2b).
  3. Go to the "Developer" tab and start the local server.
  4. The server runs at http://127.0.0.1:1234 by default.

Key difference vs cloud:
  - No API key needed (set to any non-empty string).
  - No internet connection required after the model is downloaded.
  - Speed depends on your local hardware (CPU/GPU).
"""
import os
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

# LM Studio server — change these in .env if needed
LOCAL_LLM_BASE_URL = os.getenv("LOCAL_LLM_BASE_URL", "http://127.0.0.1:1234/v1")
LOCAL_LLM_MODEL    = os.getenv("LOCAL_LLM_MODEL", "liquid/lfm2.5-1.2b")

# LM Studio doesn't require a real API key, but the client expects one
client = OpenAI(
    base_url=LOCAL_LLM_BASE_URL,
    api_key="lm-studio"
)


def ask_local_llm(user_input: str) -> None:
    print(f"\n--- Local LLM Demo (model: {LOCAL_LLM_MODEL}) ---")
    print(f"Input: \"{user_input}\"")

    response = client.chat.completions.create(
        model=LOCAL_LLM_MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user",   "content": user_input}
        ]
    )

    print(f"Response:\n{response.choices[0].message.content}")
    print(f"\n[Tokens used — prompt: {response.usage.prompt_tokens}, "
          f"completion: {response.usage.completion_tokens}]")


def list_local_models() -> None:
    """Print all models currently available in the LM Studio server."""
    print("\n--- Models available in LM Studio ---")
    models = client.models.list()
    for m in models.data:
        print(f"  - {m.id}")


if __name__ == "__main__":
    list_local_models()
    ask_local_llm("Explain what a Large Language Model is in two sentences.")
