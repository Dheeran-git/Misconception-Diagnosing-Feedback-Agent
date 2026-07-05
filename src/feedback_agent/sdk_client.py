"""The model-call seam: one function that returns a Diagnosis, live or offline.

Design (per approved plan): **offline-first with a live SDK seam.**

- ``diagnose_call(...)`` returns a validated ``Diagnosis``.
- When ``config.OFFLINE`` is set, or the Agent SDK / its auth is unavailable, we
  fall back to a deterministic **stub** (token-overlap ranking). The stub is a
  *pipeline smoke* — it proves the harness end-to-end and keeps ``pytest`` free
  and deterministic. It is NOT a reported quality metric.
- The live path uses ``claude_agent_sdk.query`` with native structured output
  (``output_format`` json_schema), verified against the installed SDK
  (v0.2.x: ResultMessage.structured_output / .result).

Callers should prefer ``diagnosis.diagnose_baseline`` which adds caching.
"""
from __future__ import annotations

import asyncio
import json
import re

from . import config
from .models import Diagnosis, DiagnosisItem

# --------------------------------------------------------------------------- #
# Offline deterministic stub
# --------------------------------------------------------------------------- #
_WORD = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def stub_diagnose(item: DiagnosisItem, candidates: list[tuple[str, str]]) -> Diagnosis:
    """Deterministic baseline: rank candidates by lexical overlap with the item.

    ``candidates`` is a list of (misconception_id, misconception_name). We score
    each candidate name against the question + the chosen (wrong) answer text and
    rank by overlap. Deterministic and free — a smoke baseline, not a real number.
    """
    context = _tokens(f"{item.question_text} {item.chosen_answer_text}")

    def score(name: str) -> tuple[int, str]:
        # (overlap desc, name asc) via negative overlap for stable deterministic sort
        return (-len(_tokens(name) & context), name)

    ranked = sorted(candidates, key=lambda c: score(c[1]))
    ranked_ids = [cid for cid, _ in ranked]
    top_id, top_name = (ranked[0] if ranked else (None, ""))
    return Diagnosis(
        misconception_id=top_id,
        label=top_name,
        evidence="(offline stub: lexical-overlap ranking — pipeline smoke, not a model diagnosis)",
        confidence=0.0,
        ranked_misconception_ids=ranked_ids,
    )


# --------------------------------------------------------------------------- #
# Live Agent SDK path
# --------------------------------------------------------------------------- #
def _build_prompt(template: str, item: DiagnosisItem, candidates: list[tuple[str, str]]) -> str:
    candidate_block = "\n".join(f"- {cid}: {name}" for cid, name in candidates)
    return template.format(
        question_text=item.question_text,
        correct_letter=item.correct_answer,
        correct_text=item.correct_answer_text,
        chosen_letter=item.chosen_answer,
        chosen_text=item.chosen_answer_text,
        candidate_block=candidate_block,
    )


def _extract_json(text: str) -> dict | None:
    """Best-effort: pull the first JSON object out of a text response."""
    if not text:
        return None
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    raw = fenced.group(1) if fenced else None
    if raw is None:
        brace = re.search(r"\{.*\}", text, re.DOTALL)
        raw = brace.group(0) if brace else None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _to_diagnosis(data: dict, valid_ids: set[str]) -> Diagnosis:
    """Validate model output into a Diagnosis, keeping only in-taxonomy IDs."""
    ranked = [str(x) for x in (data.get("ranked_misconception_ids") or []) if str(x) in valid_ids]
    top = data.get("misconception_id")
    top = str(top) if top is not None and str(top) in valid_ids else (ranked[0] if ranked else None)
    if top and top not in ranked:
        ranked = [top, *ranked]
    return Diagnosis(
        misconception_id=top,
        label=str(data.get("label", "")),
        evidence=str(data.get("evidence", "")),
        confidence=0.0,  # confidence.py fills this later (self-consistency)
        ranked_misconception_ids=ranked,
    )


async def _collect(prompt: str, options) -> tuple[dict | None, str]:
    """Run one query() and return (structured_output, concatenated_text)."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, TextBlock, query

    structured: dict | None = None
    text_result = ""
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_result += block.text
        elif isinstance(message, ResultMessage):
            structured = getattr(message, "structured_output", None) or structured
            if getattr(message, "result", None):
                text_result = str(message.result)
    return structured, text_result


async def _live_json_async(prompt: str, schema: dict, *, model: str, system_prompt: str) -> dict:
    """Generic single-shot structured call → validated JSON dict. Reused by
    remediation and the simulated learner (diagnosis has its own validation)."""
    from claude_agent_sdk import ClaudeAgentOptions

    options = ClaudeAgentOptions(
        model=model,
        system_prompt=system_prompt,
        allowed_tools=[],
        max_turns=6,  # structured output can need an extra turn to emit the result
        output_format={"type": "json_schema", "schema": schema},
    )
    structured, text = await _collect(prompt, options)
    data = structured or _extract_json(text)
    if not data:
        raise RuntimeError("live call returned no parseable JSON")
    return data


def live_json(prompt: str, schema: dict, *, model: str, system_prompt: str) -> dict:
    """Sync wrapper for a live structured JSON call. Raises on failure so callers
    can fall back to their offline stub."""
    return asyncio.run(_live_json_async(prompt, schema, model=model, system_prompt=system_prompt))


async def _check_equiv_async(a: str, b: str, model: str, trace) -> str:
    """Live agent turn that *calls* the SymPy math_check tool (FR6) and, if a
    trace is given, logs the tool call via an SDK PreToolUse hook (FR9)."""
    from claude_agent_sdk import ClaudeAgentOptions

    from .tools.math_check import math_check_server
    from .trace import sdk_tool_use_hooks

    hooks = {"PreToolUse": sdk_tool_use_hooks(trace)} if trace is not None else None
    options = ClaudeAgentOptions(
        model=model,
        mcp_servers={"math": math_check_server()},
        allowed_tools=["mcp__math__math_check"],
        max_turns=4,
        system_prompt="You verify math equivalence ONLY by calling the math_check tool.",
        hooks=hooks,
    )
    prompt = (
        f'Call the math_check tool to determine whether "{a}" and "{b}" are '
        "mathematically equivalent, then state True or False."
    )
    _, text = await _collect(prompt, options)
    return text


def check_equivalence_via_agent(a: str, b: str, *, model: str | None = None, trace=None) -> str:
    """Ask a live agent to verify equivalence by calling the SymPy tool. Returns
    the agent's final text. Raises if the SDK/auth is unavailable."""
    return asyncio.run(_check_equiv_async(a, b, model or config.FAST_MODEL, trace))


async def _live_diagnose_async(
    item: DiagnosisItem, candidates: list[tuple[str, str]], model: str, template: str
) -> Diagnosis:
    from claude_agent_sdk import ClaudeAgentOptions

    valid_ids = {cid for cid, _ in candidates}
    prompt = _build_prompt(template, item, candidates)
    schema = Diagnosis.model_json_schema()

    options = ClaudeAgentOptions(
        model=model,
        system_prompt="You are an expert mathematics teacher who diagnoses student misconceptions.",
        allowed_tools=[],
        max_turns=6,  # structured output can need an extra turn to emit the result
        output_format={"type": "json_schema", "schema": schema},
    )
    structured, text_result = await _collect(prompt, options)
    data = structured or _extract_json(text_result)
    if not data:
        raise RuntimeError("live diagnosis returned no parseable JSON")
    return _to_diagnosis(data, valid_ids)


def diagnose_call(
    item: DiagnosisItem,
    candidates: list[tuple[str, str]],
    *,
    model: str | None = None,
    template: str = "",
    force_offline: bool = False,
) -> tuple[Diagnosis, str]:
    """Return (Diagnosis, mode) where mode is 'live' or 'offline'.

    Falls back to the deterministic stub when offline is requested/configured, or
    when the live SDK path raises (e.g. headless auth unavailable) — so the
    harness never hard-fails on model access.
    """
    model = model or config.DIAGNOSIS_MODEL
    if force_offline or config.OFFLINE:
        return stub_diagnose(item, candidates), "offline"
    try:
        diagnosis = asyncio.run(_live_diagnose_async(item, candidates, model, template))
        return diagnosis, "live"
    except Exception:
        return stub_diagnose(item, candidates), "offline"
