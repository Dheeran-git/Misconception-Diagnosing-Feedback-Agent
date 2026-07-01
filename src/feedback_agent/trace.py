"""FR9 — full agent-trace logging to a file (the debugger + the demo footage).

Each loop step (and, on live calls, each SDK tool-use via a hook) is appended as a
JSON line to ``traces/<run_id>.jsonl`` (gitignored). Plain JSONL so it's trivial
to tail during a demo or diff when debugging.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import config


class TraceLogger:
    def __init__(self, run_id: str, *, sink_dir: Path | None = None):
        self.run_id = run_id
        d = Path(sink_dir) if sink_dir is not None else config.REPO_ROOT / "traces"
        d.mkdir(parents=True, exist_ok=True)
        self.path = d / f"{run_id}.jsonl"
        self._seq = 0

    def log(self, step: str, data: dict | None = None) -> None:
        self._seq += 1
        record = {"seq": self._seq, "run_id": self.run_id, "step": step, **(data or {})}
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def read(self) -> list[dict]:
        if not self.path.exists():
            return []
        return [
            json.loads(line)
            for line in self.path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]


def sdk_tool_use_hooks(trace: TraceLogger):
    """Build SDK hooks that log every tool call to the trace (used on live agent
    turns that expose tools, e.g. the math_check tool). Lazy import so offline
    code never needs the SDK."""
    from claude_agent_sdk import HookMatcher

    async def _pre_tool_use(input_data, tool_use_id, context):  # noqa: ANN001
        trace.log(
            "tool_use",
            {
                "tool": input_data.get("tool_name"),
                "tool_input": input_data.get("tool_input"),
                "tool_use_id": tool_use_id,
            },
        )
        return {}

    return [HookMatcher(matcher=None, hooks=[_pre_tool_use])]
