#!/usr/bin/env python3
"""One-time Agent SDK smoke test.

Proves the Claude Agent SDK runs on your Max plan with NO API key, before you
build anything. Run AFTER `bash preflight.sh` passes:

    python smoke_test.py

If it prints "GREEN", your whole model-access story is de-risked and you can
start Day 1. The SDK symbols used here (query, ClaudeAgentOptions, message
.result) match the current docs; if anything mismatches, confirm against:
    https://code.claude.com/docs/en/agent-sdk/python
"""
import asyncio
import os
import sys


def check_no_api_key() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        print("FAIL: ANTHROPIC_API_KEY is set. In headless/SDK mode the key overrides")
        print("      your Max subscription and bills the API. Run: unset ANTHROPIC_API_KEY")
        sys.exit(1)
    print("OK: ANTHROPIC_API_KEY is not set — SDK will use your subscription OAuth.")


async def run_query() -> str:
    try:
        from claude_agent_sdk import query, ClaudeAgentOptions
    except ImportError:
        print("FAIL: claude_agent_sdk not installed.")
        print("      Run: uv add claude-agent-sdk   (or: pip install claude-agent-sdk)")
        print("      Requires Python 3.10+.")
        sys.exit(1)

    result_text = ""
    # No tools needed for a hello-world check. allowed_tools=[] keeps it a plain
    # single-turn answer; drop the arg if your SDK version rejects an empty list.
    async for message in query(
        prompt="Respond with exactly the token SMOKE_OK and nothing else.",
        options=ClaudeAgentOptions(allowed_tools=[]),
    ):
        # The SDK's terminal message exposes `.result` (per docs examples).
        if hasattr(message, "result") and getattr(message, "result"):
            result_text = str(message.result)
    return result_text


def main() -> None:
    print("== Agent SDK smoke test ==")
    check_no_api_key()
    try:
        out = asyncio.run(run_query())
    except Exception as e:  # noqa: BLE001 — want the raw reason on a one-time check
        print(f"FAIL: SDK call raised {type(e).__name__}: {e}")
        print("Hints:")
        print("  - Auth/credit error? Run `claude`, log in with your Max plan, /status.")
        print("  - Confirm the Agent SDK credit is claimed and 'extra usage' is disabled.")
        print("  - Verify current API: https://code.claude.com/docs/en/agent-sdk/python")
        sys.exit(1)

    if "SMOKE_OK" in out:
        print(f"PASS: model replied on your subscription -> {out!r}")
        print("GREEN: the Agent SDK works on your Max plan with no API key. Start Day 1.")
    else:
        print(f"UNCLEAR: got a reply but not the token. Raw: {out!r}")
        print("Probably fine, but re-run and confirm auth with `claude` /status.")
        sys.exit(2)


if __name__ == "__main__":
    main()
