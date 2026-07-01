"""Pydantic data contracts.

Day 1 needs only ``Diagnosis`` (the output of the baseline diagnoser) and a small
``DiagnosisItem`` describing one gradable instance (a single wrong distractor with
its gold label). ``AssessResult`` / ``Intervention`` from ARCHITECTURE.md arrive
on their days; kept out now to avoid dead code.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class DiagnosisItem(BaseModel):
    """One gradable instance: a student picked one specific wrong distractor.

    The eval harness explodes each Eedi question into one of these per wrong
    option that carries a gold MisconceptionId.
    """

    question_id: str
    construct_name: str = ""
    subject_name: str = ""
    question_text: str
    correct_answer: str            # option letter, e.g. "B"
    correct_answer_text: str
    chosen_answer: str             # the wrong option letter the student picked
    chosen_answer_text: str
    gold_misconception_id: str     # Eedi gold label for this distractor


class Diagnosis(BaseModel):
    """The agent's diagnosis of the misconception behind a wrong answer.

    Matches the ARCHITECTURE.md contract. ``ranked_misconception_ids`` supports
    MAP@k scoring; ``misconception_id`` is the top-1 pick (== ranked[0] when
    present). ``confidence`` is filled by confidence.py later; the baseline sets a
    placeholder.
    """

    misconception_id: str | None = None      # None if no clear misconception
    label: str = ""
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    ranked_misconception_ids: list[str] = Field(default_factory=list)
