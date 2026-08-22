"""
Demo 3: Connecting an Agent to a Remote MCP Server

Goal:   Build an agent that looks up Azure technical documentation
        dynamically using Microsoft Learn's public MCP server.

Context: Instead of baking documentation into the system prompt,
         we give the agent a live connection to the source of truth.
         Every query goes through the MCP protocol — the agent
         discovers what tools are available, picks the right one,
         and gets back fresh, accurate docs.

Key takeaway:
         AI agents can seamlessly fetch trusted, external data
         if given the right server endpoint and tool approval logic.

Architecture:
         [  LLM Agent  ]  --MCP/HTTP-->  [ MS Learn MCP Server ]
         [  (openai)   ]  <-- results--  [ learn.microsoft.com ]

Usage:
    python 3_MCP_RemoteServer.py
"""

import asyncio
import json
import os
from dotenv import load_dotenv

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from openai import OpenAI

load_dotenv()

AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT", "").rstrip("/")
AZURE_AI_KEY      = os.getenv("AZURE_AI_KEY")
MODEL             = os.getenv("AZURE_AI_MODEL", "gpt-4o-mini")

MS_LEARN_MCP_URL  = "https://learn.microsoft.com/api/mcp"

SEP = "-" * 64


def mcp_tool_to_openai(tool) -> dict:
    """Convert an MCP tool definition to an OpenAI-style tool dict."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.inputSchema if tool.inputSchema else {"type": "object", "properties": {}},
        },
    }


async def run_agent(user_query: str):
    print(f"\n{SEP}")
    print(f"  User question: {user_query}")
    print(SEP)

    llm = OpenAI(base_url=AZURE_AI_ENDPOINT, api_key=AZURE_AI_KEY)

    print(f"\n  Connecting to MS Learn MCP server...")
    print(f"  URL: {MS_LEARN_MCP_URL}")

    async with streamablehttp_client(url=MS_LEARN_MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Discover available tools
            tools_result = await session.list_tools()
            tools = tools_result.tools
            print(f"  Tools available from MS Learn MCP: {len(tools)}")
            for t in tools[:5]:
                print(f"    - {t.name}: {(t.description or '')[:70]}")
            if len(tools) > 5:
                print(f"    … and {len(tools) - 5} more")

            openai_tools = [mcp_tool_to_openai(t) for t in tools]

            messages = [
                {"role": "system", "content": (
                    "You are a helpful Azure documentation assistant. "
                    "Use the available tools to look up accurate, up-to-date "
                    "information from Microsoft Learn documentation. "
                    "Always cite which docs you consulted."
                )},
                {"role": "user", "content": user_query},
            ]

            max_iterations = 5
            for iteration in range(1, max_iterations + 1):
                print(f"\n  [Iteration {iteration}] Calling LLM...")

                response = llm.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=openai_tools,
                    tool_choice="auto",
                )
                msg = response.choices[0].message

                if not msg.tool_calls:
                    print(f"\n{SEP}")
                    print("  AGENT ANSWER:")
                    print(SEP)
                    print(msg.content)
                    print()
                    break

                messages.append(msg)

                for tc in msg.tool_calls:
                    fn_name = tc.function.name
                    fn_args = json.loads(tc.function.arguments)

                    print(f"\n  [Tool call] {fn_name}")
                    print(f"    args: {json.dumps(fn_args)[:200]}")
                    print(f"    Approved - executing via MCP...")

                    result = await session.call_tool(fn_name, fn_args)
                    tool_output = result.content[0].text if result.content else "{}"

                    print(f"    Result preview: {tool_output[:200]}...")

                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": tool_output,
                    })
            else:
                print("  Max iterations reached without a final answer.")


async def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 64)
    print("  Demo 3: Agent + Remote MCP Server")
    print("  Connecting to Microsoft Learn documentation")
    print("=" * 64)
    print()
    print("  The agent will use MCP to query live Azure docs.")
    print("  No static docs are embedded in the system prompt.")
    print()

    queries = [
        "What is Azure AI Search and what are its main pricing tiers?",
        "How do I enable semantic search on an Azure AI Search index?",
    ]

    for query in queries:
        await run_agent(query)
        print()
        input("  Press Enter for next query...")
        print()

    print("=" * 64)
    print("  Key Concept:")
    print("  The agent never hardcoded any docs. It discovered available")
    print("  tools from the MCP server at runtime, called them, and")
    print("  grounded its answers in the live documentation.")
    print("=" * 64)
    print()


if __name__ == "__main__":
    asyncio.run(main())
