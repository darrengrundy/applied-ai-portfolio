"""Compare prompt versions for a trail-guide agent using OpenTelemetry tracing.

Instruments Chat Completions calls with Azure Monitor OpenTelemetry so each
prompt version's token usage and latency can be compared in Application
Insights, mirroring the exercise's v1/v2/v3 prompt-iteration comparison in a
single, self-contained script rather than the full scaffolded lab repository.
"""

import os
import time
from pathlib import Path

from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.monitor.opentelemetry import configure_azure_monitor
from dotenv import load_dotenv
from openai import OpenAI
from opentelemetry import trace
from opentelemetry.instrumentation.openai_v2 import OpenAIInstrumentor

PROMPTS_DIR = Path(__file__).parent / "prompts"
VERSIONS = ["v1", "v2", "v3"]
TEST_QUESTIONS = [
    "What should I pack for a day hike in cold weather?",
    "How difficult is a 10km trail with 400m of elevation gain?",
    "What's the earliest safe start time for a summer hike?",
]

tracer = trace.get_tracer(__name__)


def require_setting(name: str) -> str:
    """Return a required environment setting or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment setting: {name}")
    return value


def load_system_prompt(version: str) -> str:
    """Read a versioned system prompt from the local prompts directory."""
    path = PROMPTS_DIR / f"{version}_system_prompt.txt"
    return path.read_text(encoding="utf-8").strip()


def run_version(client: OpenAI, deployment: str, version: str) -> None:
    """Run every test question for one prompt version inside a root span."""
    system_prompt = load_system_prompt(version)
    with tracer.start_as_current_span(f"trail_guide_{version}"):
        for index, question in enumerate(TEST_QUESTIONS, start=1):
            span_name = f"{version}_test-{index}"
            with tracer.start_as_current_span(span_name) as span:
                start = time.perf_counter()
                response = client.chat.completions.create(
                    model=deployment,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question},
                    ],
                )
                duration_s = time.perf_counter() - start
                total_tokens = response.usage.total_tokens if response.usage else 0
                span.set_attribute("response.total_tokens", total_tokens)
                span.set_attribute("response.duration_s", duration_s)

                preview = response.choices[0].message.content[:120]
                print(
                    f"[{span_name}] {duration_s * 1000:.0f}ms, "
                    f"tokens={total_tokens} :: {preview}..."
                )


def main() -> None:
    load_dotenv()
    connection_string = require_setting("APPLICATIONINSIGHTS_CONNECTION_STRING")
    endpoint = require_setting("AZURE_OPENAI_ENDPOINT")
    deployment = require_setting("MODEL_DEPLOYMENT")

    configure_azure_monitor(connection_string=connection_string)
    OpenAIInstrumentor().instrument()

    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://ai.azure.com/.default"
    )
    client = OpenAI(base_url=endpoint, api_key=token_provider)

    for version in VERSIONS:
        run_version(client, deployment, version)

    print(
        "\nDone. Compare span durations and token counts across versions in "
        "Application Insights (Foundry portal > Monitoring > Resource usage)."
    )


if __name__ == "__main__":
    main()
