"""Main entry point for the MCP tool abuse demo."""

import asyncio
import os
import sys

from src.agent import create_debug_assistant
from src.models import DebugRequest, DebugResponse


def print_response(response: DebugResponse) -> None:
    """Print the agent's response.

    Args:
        response: The debugging response from the agent.
    """
    print("\n" + "=" * 70)
    print("🤖 DEBUGGING ASSISTANT RESPONSE")
    print("=" * 70)
    print(response.answer)

    if response.sources_consulted:
        print("\n📚 Sources consulted:")
        for source in response.sources_consulted:
            print(f"   - {source}")

    print("=" * 70 + "\n")


async def main() -> None:
    """Run the MCP tool abuse demo."""
    # Get user message from environment variable
    user_message = os.getenv("USER_MESSAGE")

    if not user_message:
        print("❌ ERROR: USER_MESSAGE environment variable is required.", file=sys.stderr)
        print("\nUsage:", file=sys.stderr)
        print('  USER_MESSAGE="Your debug question here" docker compose up', file=sys.stderr)
        sys.exit(1)

    print("\n" + "=" * 70)
    print("🔍 TECHNICAL DEBUGGING ASSISTANT")
    print("=" * 70)
    print("\n📝 User Message:")
    print("-" * 70)
    print(user_message)
    print("-" * 70)

    print("\n🤖 Creating debugging assistant agent...")
    flock, _ = create_debug_assistant()

    print("📡 Connecting to MCP servers...")
    print("   - Microsoft Docs MCP")
    print("   - Weather MCP")

    print("\n🔄 Processing request...\n")

    # Create the debug request
    request = DebugRequest(message=user_message)
    await flock.publish(request)

    # Run agent until idle
    await flock.run_until_idle()

    # Retrieve response
    responses = await flock.store.get_by_type(DebugResponse)

    if responses:
        print_response(responses[0])
    else:
        print("❌ No response generated.", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())
