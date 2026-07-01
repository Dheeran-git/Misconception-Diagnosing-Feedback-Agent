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


async def _live_diagnose_async(
    item: DiagnosisItem, candidates: list[tuple[str, str]], model: str, template: str
) -> Diagnosis:
    from claude_agent_sdk import (  # imported lazily so offline never needs the SDK
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )

    valid_ids = {cid for cid, _ in candidates}
    prompt = _build_prompt(template, item, candidates)
    schema = Diagnosis.model_json_schema()

    options = ClaudeAgentOptions(
        model=model,
        system_prompt="You are an expert mathematics teacher who diagnoses student misconceptions.",
        allowed_tools=[],
        max_turns=1,
        output_format={"type": "json_schema", "schema": schema},
    )

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
