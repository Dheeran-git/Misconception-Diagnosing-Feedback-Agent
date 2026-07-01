"""Pydantic data contracts.

Day 1: ``Diagnosis`` + ``DiagnosisItem``. Day 2: ``AssessResult`` (FR1 ASSESS).
Day 4: ``Intervention`` (remediation) + ``LearnerAttempt`` (simulated learner).
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


class AssessResult(BaseModel):
    """FR1 ASSESS: is the student's chosen MCQ answer correct, and which option?

    For MCQ this is a deterministic option-letter comparison, so ``confidence`` is
    1.0 — there is no model call to be uncertain about. The rubric fields exist
    only for the *optional* ASAP-SAS free-response stretch (EVAL.md) and stay
    ``None`` on the MCQ spine.
    """

    question_id: str
    is_correct: bool
    chosen_answer: str                 # option letter the student picked
    chosen_answer_text: str = ""
    correct_answer: str                # the correct option letter
    correct_answer_text: str = ""
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    # optional (ASAP free-response stretch only):
    rubric_score: float | None = None
    per_criterion: dict[str, float] | None = None


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


class Intervention(BaseModel):
    """FR3 REMEDIATE: a targeted Socratic hint that must not reveal the answer.

    ``escalation_level`` 0 is the first hint; each unresolved verify bumps it.
    ``leaked_answer`` is set by the guardrail if the text revealed the final
    answer (the agent regenerates / redacts rather than showing a leak).
    """

    text: str
    targets_misconception_id: str | None = None
    escalation_level: int = 0
    leaked_answer: bool = False


class LearnerAttempt(BaseModel):
    """A simulated learner's answer on an attempt.

    ``answer`` is the free-form value the student arrives at (e.g. "x = 8"),
    checked against the correct answer via grading.answers_equivalent — so the
    learner never needs the full option list, only to solve the problem.
    """

    answer: str
    reasoning: str = ""
