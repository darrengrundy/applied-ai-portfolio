"""
Demo 4: Agent + Custom MCP Server — Inventory Assistant

An AI agent backed by a custom MCP server (inventory_server.py).
The agent discovers the server's tools at runtime and uses them
to answer any inventory question you ask in the chat loop.

Key concept:
    Your private Python logic (the inventory dict) is never
    exposed directly to the AI. All data flows through the MCP
    protocol — structured and controlled by the server you built.

Architecture:
    [  LLM Agent  ]  --stdio/MCP-->  [ inventory_server.py ]
    [  (openai)   ]  <-tool result-  [ (FastMCP server)    ]

Usage:
    python 4_MCP_CustomInventory.py
"""

import asyncio
import json
import os
import sys
from contextlib import AsyncExitStack
from dotenv import load_dotenv

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

load_dotenv()

AZURE_AI_ENDPOINT = os.getenv("AZURE_AI_ENDPOINT", "").rstrip("/")
AZURE_AI_KEY      = os.getenv("AZURE_AI_KEY")
MODEL             = os.getenv("AZURE_AI_MODEL", "gpt-4o-mini")


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


async def connect_to_server(exit_stack: AsyncExitStack):
    """Start inventory_server.py as a subprocess and return an MCP session."""
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "inventory_server.py")

    server_params = StdioServerParameters(
        command=sys.executable,
        args=[server_script],
        env=None,
    )

    read, write = await exit_stack.enter_async_context(stdio_client(server_params))
    session = await exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    return session


async def chat_loop(session: ClientSession):
    """Interactive chat loop — ask the inventory agent anything."""

    # Discover tools exposed by the MCP server
    response = await session.list_tools()
    tools = response.tools

    print(f"  MCP server connected. Tools available: {len(tools)}")
    for t in tools:
        print(f"    - {t.name}: {(t.description or '').splitlines()[0]}")
    print()

    openai_tools = [mcp_tool_to_openai(t) for t in tools]

    llm = OpenAI(base_url=AZURE_AI_ENDPOINT, api_key=AZURE_AI_KEY)

    messages = [
        {"role": "system", "content": (
            "You are a helpful retail inventory assistant. "
            "Use the available tools to answer questions about stock levels "
            "and weekly sales. Be specific and include numbers in your answers."
        )},
    ]

    while True:
        user_input = input("\nEnter a prompt for the inventory agent (or 'quit' to exit).\nUSER: ").strip()
        if user_input.lower() == "quit":
            print("Exiting chat.")
            break

        messages.append({"role": "user", "content": user_input})

        for _ in range(8):
            response = llm.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=openai_tools,
                tool_choice="auto",
            )
            msg = response.choices[0].message

            if not msg.tool_calls:
                print(f"\nASSISTANT: {msg.content}")
                messages.append({"role": "assistant", "content": msg.content or ""})
                break

            messages.append(msg)

            for tc in msg.tool_calls:
                fn_name = tc.function.name
                fn_args = json.loads(tc.function.arguments)

                print(f"\n  [Tool] {fn_name}({json.dumps(fn_args) if fn_args else ''})")

                result = await session.call_tool(fn_name, fn_args)
                tool_output = result.content[0].text if result.content else "{}"

                print(f"  [Result] {tool_output[:300]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": tool_output,
                })


async def main():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 64)
    print("  Demo 4: Agent + Custom MCP Inventory Server")
    print("=" * 64)
    print()
    print("  Starting inventory_server.py via stdio transport...")
    print()

    exit_stack = AsyncExitStack()
    try:
        session = await connect_to_server(exit_stack)
        await chat_loop(session)
    finally:
        await exit_stack.aclose()


if __name__ == "__main__":
    asyncio.run(main())
