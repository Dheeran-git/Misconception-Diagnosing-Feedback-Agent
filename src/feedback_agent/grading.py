"""FR1 ASSESS: the front of the agent loop.

Given an MCQ math item and the student's chosen option, decide correctness and
build the context the diagnosis step needs. For multiple-choice this is a
*deterministic* option-letter comparison — no model call, so it is free, exact,
and needs no cache. That determinism is a feature: the ASSESS step can never be
the source of a wrong headline number.

``answers_equivalent`` is a seam: today it compares option letters (and, as a
convenience, normalized answer text). The SymPy-backed symbolic/numeric
equivalence tool (FR6) plugs in here on Day 4 without changing this signature —
it is only needed when we compare free-form answer *expressions* rather than
MCQ letters.
"""
from __future__ import annotations

import sqlite3

from . import state
from .models import AssessResult, DiagnosisItem

# Version tag for the ASSESS logic; part of the grade_cache key. Bump if the
# assess rule changes (e.g. when free-response model grading is added).
ASSESS_VERSION = "assess_mcq_v1"
_ASSESS_MODEL = "deterministic"  # MCQ assess makes no model call


def _norm(s: str) -> str:
    return " ".join(str(s).strip().lower().split())


def answers_equivalent(a: str, b: str) -> bool:
    """Whether two answers match, using the SymPy math-equivalence tool (FR6) so
    "1/2" == "0.5" and "2x+3" == "3+2x". Falls back to a normalized string compare
    for option letters / unparseable text. Never raises."""
    try:
        from .tools.math_check import math_equivalent

        return math_equivalent(a, b).equivalent
    except Exception:
        return _norm(a) == _norm(b)


def assess(
    question_id: str,
    chosen_answer: str,
    correct_answer: str,
    *,
    chosen_answer_text: str = "",
    correct_answer_text: str = "",
) -> AssessResult:
    """Assess one MCQ answer. Deterministic; confidence is 1.0."""
    is_correct = answers_equivalent(chosen_answer, correct_answer)
    return AssessResult(
        question_id=question_id,
        is_correct=is_correct,
        chosen_answer=str(chosen_answer).strip().upper(),
        chosen_answer_text=chosen_answer_text,
        correct_answer=str(correct_answer).strip().upper(),
        correct_answer_text=correct_answer_text,
        confidence=1.0,
    )


def assess_choice(
    item: DiagnosisItem, chosen_answer: str, chosen_answer_text: str = ""
) -> AssessResult:
    """Assess a chosen option against a question record's correct answer.

    ``item`` carries the correct answer; ``chosen_answer`` is what the student
    actually picked (may differ from ``item.chosen_answer``, which is the specific
    distractor the eval instance is *about*).
    """
    return assess(
        item.question_id,
        chosen_answer,
        item.correct_answer,
        chosen_answer_text=chosen_answer_text,
        correct_answer_text=item.correct_answer_text,
    )


def assess_cached(
    conn: sqlite3.Connection,
    question_id: str,
    chosen_answer: str,
    correct_answer: str,
    *,
    chosen_answer_text: str = "",
    correct_answer_text: str = "",
    log: bool = True,
) -> tuple[AssessResult, str]:
    """Assess via the grade_cache. Returns (AssessResult, mode).

    mode is 'cache' on a hit, 'computed' on a miss. On a miss we also log the
    attempt (FR7). For MCQ the computation is deterministic, so the cache only
    demonstrates the pattern here — but the same path saves credit once ASSESS
    becomes model-driven (free-response stretch).
    """
    key = state.grade_key(question_id, chosen_answer, ASSESS_VERSION, _ASSESS_MODEL)
    cached = state.get_grade(conn, key)
    if cached is not None:
        return cached, "cache"

    result = assess(
        question_id,
        chosen_answer,
        correct_answer,
        chosen_answer_text=chosen_answer_text,
        correct_answer_text=correct_answer_text,
    )
    state.set_grade(
        conn,
        key,
        question_id=question_id,
        model=_ASSESS_MODEL,
        prompt_version=ASSESS_VERSION,
        grade=result,
    )
    if log:
        state.log_attempt(
            conn,
            question_id=question_id,
            step="assess",
            payload=result.model_dump_json(),
            chosen_answer=result.chosen_answer,
        )
    return result, "computed"
