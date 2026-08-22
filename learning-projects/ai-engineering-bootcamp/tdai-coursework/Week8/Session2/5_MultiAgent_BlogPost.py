"""
Demo 5: Multi-Agent Blog Post Pipeline using Azure AI Foundry Responses API

Two agents, each with a focused role:
  - Title Agent   -> generates 3 headline options for a topic
  - Outline Agent -> structures a full article from the chosen title

The orchestrator routes work between them sequentially.

Usage:
    python 5_MultiAgent_BlogPost.py
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

ENDPOINT = os.getenv("AZURE_AI_ENDPOINT", "").rstrip("/")
API_KEY  = os.getenv("AZURE_AI_KEY")
MODEL    = os.getenv("AZURE_AI_MODEL", "gpt-4o-mini")

SEP  = "-" * 64
SEP2 = "-" * 64


def title_agent(client: OpenAI, topic: str) -> list[str]:
    print(f"\n{SEP2}")
    print("  [Title Agent] Generating headlines...")
    print(SEP2)

    response = client.responses.create(
        model=MODEL,
        instructions=(
            "You are a technical blog post title specialist. "
            "Output exactly 3 title options, numbered 1. 2. 3. "
            "Each title must be under 70 characters. "
            "Use concrete language. No markdown."
        ),
        input=f"Generate 3 blog post titles for: {topic}",
    )

    raw = response.output_text
    print(f"\n{raw}\n")

    titles = []
    for line in raw.splitlines():
        line = line.strip()
        if line and line[0].isdigit() and ". " in line:
            titles.append(line.split(". ", 1)[1].strip())

    return titles or [raw]


def outline_agent(client: OpenAI, title: str) -> str:
    print(f"\n{SEP2}")
    print(f"  [Outline Agent] Structuring: '{title}'")
    print(SEP2)

    response = client.responses.create(
        model=MODEL,
        instructions=(
            "You are a technical article outline specialist. "
            "Produce a structured outline a developer could follow. "
            "Include: Introduction, 4-6 sections each with bullet points "
            "and code examples to include, Conclusion, Estimated reading time."
        ),
        input=f"Create a full article outline for: '{title}'",
    )

    return response.output_text


def main():
    os.system("cls" if os.name == "nt" else "clear")
    print(SEP)
    print("  Demo 5: Multi-Agent Blog Post Pipeline")
    print("  Title Agent -> Outline Agent  (Azure AI Foundry Responses API)")
    print(SEP)

    client = OpenAI(base_url=ENDPOINT, api_key=API_KEY)
    topic  = "Building AI agents with Azure AI Search and MCP tools"

    titles = title_agent(client, topic)
    chosen = titles[0]
    print(f"  Selected title: '{chosen}'")

    outline = outline_agent(client, chosen)

    print(f"\n{SEP}")
    print(f"  FINAL OUTLINE — {chosen}")
    print(SEP)
    print(outline)
    print()


if __name__ == "__main__":
    main()
