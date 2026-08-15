"""Console client for a Foundry-hosted IT support agent.

Talks to a named Foundry "prompt agent" (created in the Foundry portal with
file_search and code_interpreter tools, grounded on IT_Policy.txt and
system_performance.csv) through the Responses API's agent_reference
extension, rather than calling a raw model deployment directly.
"""

import base64
import os
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

OUTPUT_DIR = Path("agent_outputs")


def require_setting(name: str) -> str:
    """Return a required environment setting or raise a clear error."""
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment setting: {name}")
    return value


def get_output_path(filename: str) -> Path:
    """Return a unique local path for a file the agent generates."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / filename
    counter = 1
    while path.exists():
        stem, suffix = Path(filename).stem, Path(filename).suffix
        path = OUTPUT_DIR / f"{stem}_{counter}{suffix}"
        counter += 1
    return path


def save_image(image_base64: str, filename: str) -> Path:
    """Decode a base64 image payload and save it locally."""
    path = get_output_path(filename)
    path.write_bytes(base64.b64decode(image_base64))
    return path


def format_output_text(response) -> str:
    """Extract display text and note any generated files in the response.

    Foundry agent responses can include ordinary text plus code-interpreter
    output items (charts, computed files). This walks the response output
    items defensively, since the exact item shape has changed as the
    Responses API's agent support has evolved.
    """
    lines: list[str] = []
    for item in getattr(response, "output", []) or []:
        item_type = getattr(item, "type", None)
        if item_type == "message":
            for content in getattr(item, "content", []) or []:
                text = getattr(content, "text", None)
                if text:
                    lines.append(text)
        elif item_type == "code_interpreter_call":
            outputs = getattr(item, "outputs", []) or []
            for output in outputs:
                if getattr(output, "type", None) == "image" and getattr(
                    output, "image_base64", None
                ):
                    saved = save_image(output.image_base64, "chart.png")
                    lines.append(f"[Saved generated chart to {saved}]")
    if not lines and getattr(response, "output_text", None):
        lines.append(response.output_text)
    return "\n".join(lines) if lines else "(no text content in response)"


def main() -> None:
    load_dotenv()
    project_endpoint = require_setting("PROJECT_ENDPOINT")
    agent_name = require_setting("AGENT_NAME")

    project_client = AIProjectClient(
        endpoint=project_endpoint, credential=DefaultAzureCredential()
    )
    openai_client = project_client.get_openai_client()

    previous_response_id = None
    print(f"Connected to agent '{agent_name}'. Type 'exit', 'quit', or 'bye' to end.\n")

    while True:
        prompt = input("You: ").strip()
        if prompt.lower() in {"exit", "quit", "bye"}:
            break
        if not prompt:
            continue

        response = openai_client.responses.create(
            input=prompt,
            previous_response_id=previous_response_id,
            extra_body={
                "agent_reference": {"name": agent_name, "type": "agent_reference"}
            },
        )
        print(f"\nAgent: {format_output_text(response)}\n")
        previous_response_id = response.id


if __name__ == "__main__":
    main()
