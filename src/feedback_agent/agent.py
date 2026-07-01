"""The feedback agent loop — the differentiator, kept as explicit Python.

State machine (ARCHITECTURE.md):

    ASSESS ─correct─────────────────────────────► DONE (nothing to fix)
      │ wrong
      ▼
    DIAGNOSE ─► REMEDIATE ─► (learner re-attempts) ─► VERIFY
                                                       │ resolved ─► DONE
                                                       │ not resolved
                                                       ▼
                                                    ESCALATE (≤ N) ─► back to REMEDIATE
                                                       │ cap reached
                                                       ▼
                                                    ROUTE TO TEACHER TRIAGE

Every decision (when to escalate, when to route to triage) is made by *our* code,
not hidden in a framework, so a human can explain each step. Each step is logged
to the attempts table (FR7) and returned in the trace (FR9). Confidence-based
triage routing is wired here but real confidence values arrive in confidence.py
(Day 5); today we route on *unresolved-after-escalation*.
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from typing import Protocol

from . import config, state
from .diagnosis import diagnose_baseline
from .grading import answers_equivalent
from .models import Diagnosis, DiagnosisItem, Intervention, LearnerAttempt
from .remediation import generate_intervention


class Learner(Protocol):
    """Anything that can attempt an item (the simulated learner, or a real UI)."""

    def attempt(
        self,
        item: DiagnosisItem,
        intervention: Intervention | None = None,
        *,
        force_offline: bool = ...,
    ) -> tuple[LearnerAttempt, str]:
        ...


class Retriever(Protocol):
    def candidates(self, item: DiagnosisItem, k: int | None = ...) -> list[tuple[str, str]]:
        ...


@dataclass
class LoopResult:
    question_id: str
    arm: str                       # 'targeted' | 'generic'
    unaided_correct: bool
    resolved: bool
    interventions_used: int        # hints given (0 if solved unaided)
    escalations_used: int          # = max(0, interventions_used - 1)
    routed_to_triage: bool
    diagnosis: Diagnosis | None = None
    steps: list[dict] = field(default_factory=list)


def run_loop(
    item: DiagnosisItem,
    learner: Learner,
    retriever: Retriever,
    *,
    arm: str = "targeted",
    conn: sqlite3.Connection | None = None,
    force_offline: bool = False,
    max_escalations: int | None = None,
    diagnosis_model: str | None = None,
    remediation_model: str | None = None,
    k: int | None = None,
) -> LoopResult:
    """Run the full loop for one item + learner. ``arm`` selects targeted vs
    generic remediation (the efficacy experiment's two conditions)."""
    max_escalations = config.MAX_ESCALATIONS if max_escalations is None else max_escalations
    targeted = arm == "targeted"
    own_conn = conn is None
    if conn is None:
        conn = state.connect()

    steps: list[dict] = []

    def record(step: str, payload: dict) -> None:
        steps.append({"step": step, **payload})
        state.log_attempt(
            conn,
            question_id=item.question_id,
            step=step,
            payload=json.dumps(payload, default=str),
            chosen_answer=item.chosen_answer,
        )

    try:
        # 1) ASSESS — the learner's unaided attempt.
        first, _ = learner.attempt(item, None, force_offline=force_offline)
        unaided_correct = answers_equivalent(first.answer, item.correct_answer_text)
        record("assess", {"answer": first.answer, "correct": unaided_correct})
        if unaided_correct:
            return LoopResult(
                question_id=item.question_id, arm=arm, unaided_correct=True, resolved=True,
                interventions_used=0, escalations_used=0, routed_to_triage=False, steps=steps,
            )

        # 2) DIAGNOSE the misconception behind the wrong answer.
        candidates = retriever.candidates(item, k=k if k is not None else config.RETRIEVAL_K)
        diagnosis, _ = diagnose_baseline(
            item, candidates, conn=conn, force_offline=force_offline, model=diagnosis_model
        )
        record(
            "diagnose",
            {"misconception_id": diagnosis.misconception_id, "label": diagnosis.label},
        )

        # 3) REMEDIATE → VERIFY → ESCALATE (capped).
        resolved = False
        interventions = 0
        for level in range(max_escalations + 1):
            iv, _ = generate_intervention(
                item, diagnosis, escalation_level=level, targeted=targeted,
                model=remediation_model, force_offline=force_offline,
            )
            interventions += 1
            attempt, _ = learner.attempt(item, iv, force_offline=force_offline)
            resolved = answers_equivalent(attempt.answer, item.correct_answer_text)
            record(
                "escalate" if level > 0 else "remediate",
                {
                    "level": level,
                    "leaked_answer": iv.leaked_answer,
                    "answer": attempt.answer,
                    "resolved": resolved,
                },
            )
            if resolved:
                break

        # 4) ROUTE unresolved cases to the teacher triage queue (FR5).
        routed = not resolved
        if routed:
            state.enqueue_triage(
                conn, question_id=item.question_id, diagnosis=diagnosis,
                confidence=diagnosis.confidence,
            )
            record("triage", {"reason": "unresolved after escalation cap"})

        return LoopResult(
            question_id=item.question_id, arm=arm, unaided_correct=False, resolved=resolved,
            interventions_used=interventions, escalations_used=max(0, interventions - 1),
            routed_to_triage=routed, diagnosis=diagnosis, steps=steps,
        )
    finally:
        if own_conn:
            conn.close()
