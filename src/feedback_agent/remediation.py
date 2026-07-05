"""FR3 REMEDIATE: generate a targeted Socratic intervention (no answer leak).

Two arms (for the efficacy experiment): ``targeted`` uses the diagnosed
misconception; ``generic`` gives topic-blind encouragement (the control).

**Guardrail:** an intervention must never reveal the final answer. ``leaks_answer``
checks the text against the correct answer's value; if a live generation leaks, we
regenerate once with a stronger instruction and, failing that, fall back to a safe
templated hint. The offline stub never leaks by construction.
"""
from __future__ import annotations

import re

from . import config
from .models import Diagnosis, DiagnosisItem, Intervention
from .prompts import (
    REMEDIATE_GENERIC_VERSION,
    REMEDIATE_TARGETED_VERSION,
    load_prompt,
)
from .sdk_client import live_json

_NUM = re.compile(r"-?\d+(?:\.\d+)?")


def _answer_values(correct_answer_text: str, correct_letter: str) -> set[str]:
    """The strings that would count as revealing the answer."""
    vals: set[str] = set()
    txt = (correct_answer_text or "").strip().lower()
    if txt:
        vals.add(txt)
        # the bare value, e.g. "x = 4" -> "4"
        nums = _NUM.findall(txt)
        vals.update(nums)
    return {v for v in vals if v}


def leaks_answer(text: str, correct_answer_text: str, correct_letter: str = "") -> bool:
    """True if the intervention reveals the correct value or option letter."""
    low = f" {text.lower()} "
    for val in _answer_values(correct_answer_text, correct_letter):
        # Match each forbidden value as a standalone token, not as part of a
        # longer number/word/fraction — so the value "4" doesn't fire inside
        # "1/4" or "x/4", and the phrase "x = 4" doesn't fire inside "x = 40".
        if re.search(rf"(?<![\w./]){re.escape(val)}(?![\w./])", low):
            return True
    return False


def _stub_intervention(
    item: DiagnosisItem, diagnosis: Diagnosis, escalation_level: int, targeted: bool
) -> Intervention:
    if targeted and diagnosis.misconception_id is not None:
        text = (
            f"Let's look again at how you handled this step. {diagnosis.label} "
            "Try re-doing just that operation slowly and check whether it really "
            "keeps both sides balanced. What do you notice?"
        )
    else:
        text = (
            "Nice effort — give it another go. Re-read the question carefully and "
            "check each step of your working. Where might a small slip have crept in?"
        )
    return Intervention(
        text=text,
        targets_misconception_id=diagnosis.misconception_id if targeted else None,
        escalation_level=escalation_level,
        leaked_answer=False,
    )


def _safe_fallback(diagnosis: Diagnosis, escalation_level: int, targeted: bool) -> Intervention:
    """Templated, guaranteed-no-leak hint used if a live generation keeps leaking."""
    text = (
        "Take another careful look at the step where the error crept in, and redo "
        "just that part slowly. Check that whatever you do to one side you also do "
        "to the other."
    )
    return Intervention(
        text=text,
        targets_misconception_id=diagnosis.misconception_id if targeted else None,
        escalation_level=escalation_level,
        leaked_answer=False,
    )


def _build_prompt(item: DiagnosisItem, diagnosis: Diagnosis, escalation_level: int, targeted: bool):
    if targeted:
        tmpl = load_prompt(REMEDIATE_TARGETED_VERSION)
        return tmpl.format(
            question_text=item.question_text,
            chosen_letter=item.chosen_answer,
            chosen_text=item.chosen_answer_text,
            misconception_label=diagnosis.label,
            evidence=diagnosis.evidence,
            misconception_id=diagnosis.misconception_id,
            escalation_level=escalation_level,
        )
    tmpl = load_prompt(REMEDIATE_GENERIC_VERSION)
    return tmpl.format(
        question_text=item.question_text,
        chosen_letter=item.chosen_answer,
        chosen_text=item.chosen_answer_text,
    )


def generate_intervention(
    item: DiagnosisItem,
    diagnosis: Diagnosis,
    *,
    escalation_level: int = 0,
    targeted: bool = True,
    model: str | None = None,
    force_offline: bool = False,
) -> tuple[Intervention, str]:
    """Return (Intervention, mode). mode is 'live' or 'offline'.

    Applies the no-answer-leak guardrail: on a leaking live generation, retries
    once, then falls back to a safe templated hint (never shows a leak).
    """
    model = model or config.FAST_MODEL
    if force_offline or config.OFFLINE:
        return _stub_intervention(item, diagnosis, escalation_level, targeted), "offline"

    schema = Intervention.model_json_schema()
    system = "You are an encouraging, Socratic mathematics tutor."
    try:
        for attempt in range(2):
            prompt = _build_prompt(item, diagnosis, escalation_level, targeted)
            if attempt == 1:
                prompt += (
                    "\n\nIMPORTANT: your previous attempt revealed the answer. Do NOT "
                    "state the final value or option letter; only guide the student."
                )
            data = live_json(prompt, schema, model=model, system_prompt=system)
            iv = Intervention(
                text=str(data.get("text", "")),
                targets_misconception_id=(diagnosis.misconception_id if targeted else None),
                escalation_level=escalation_level,
            )
            if not leaks_answer(iv.text, item.correct_answer_text, item.correct_answer):
                return iv, "live"
        # both attempts leaked -> safe fallback
        return _safe_fallback(diagnosis, escalation_level, targeted), "live"
    except Exception:
        return _stub_intervention(item, diagnosis, escalation_level, targeted), "offline"
