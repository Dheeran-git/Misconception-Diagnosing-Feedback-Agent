"""Batch misconception-tagging pipeline with confidence + triage (FR5).

This is the scalability story: tag a batch of wrong-answer distractors, auto-
finalize the confident ones, and route the rest to the teacher tagging-review
queue. Produces the headline numbers — % auto-taggable and teacher-time-saved —
plus the accuracy held on the auto-tagged slice.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from feedback_agent import config, state
from feedback_agent.confidence import diagnose_with_confidence, should_triage
from feedback_agent.models import DiagnosisItem
from feedback_agent.taxonomy import build_retriever

from . import metrics as M


@dataclass
class TaggingResult:
    metrics: dict[str, float]
    records: list[dict] = field(default_factory=list)
    n_triaged: int = 0


def run_tagging(
    items: list[DiagnosisItem],
    mapping: dict[str, str],
    *,
    k: int | None = None,
    threshold: float | None = None,
    conn: sqlite3.Connection | None = None,
    force_offline: bool = False,
    retriever=None,
) -> TaggingResult:
    threshold = config.TRIAGE_CONFIDENCE_THRESHOLD if threshold is None else threshold
    own_conn = conn is None
    if conn is None:
        conn = state.connect()
    if retriever is None:
        retriever = build_retriever(mapping)

    preds: list[str | None] = []
    gold: list[str] = []
    confs: list[float] = []
    records: list[dict] = []
    n_triaged = 0
    try:
        for item in items:
            candidates = retriever.candidates(item, k=config.RETRIEVAL_K)
            diagnosis, picks = diagnose_with_confidence(
                item, candidates, k=k, conn=conn, force_offline=force_offline
            )
            triaged = should_triage(diagnosis.confidence, threshold)
            if triaged:
                state.enqueue_triage(
                    conn, question_id=item.question_id, diagnosis=diagnosis,
                    confidence=diagnosis.confidence,
                )
                n_triaged += 1
            preds.append(diagnosis.misconception_id)
            gold.append(item.gold_misconception_id)
            confs.append(diagnosis.confidence)
            records.append(
                {
                    "question_id": item.question_id,
                    "gold": item.gold_misconception_id,
                    "pred": diagnosis.misconception_id,
                    "confidence": diagnosis.confidence,
                    "picks": picks,
                    "auto_tagged": not triaged,
                    "correct": diagnosis.misconception_id == item.gold_misconception_id,
                }
            )
    finally:
        if own_conn:
            conn.close()

    summary = M.auto_taggable_summary(preds, gold, confs, threshold=threshold)
    return TaggingResult(metrics=summary, records=records, n_triaged=n_triaged)


def format_tagging(result: TaggingResult, threshold: float) -> str:
    m = result.metrics
    return "\n".join(
        [
            f"=== Batch tagging (confidence threshold {threshold:.2f}) ===",
            f"  n                     {int(m['n'])}",
            f"  overall top-1         {m['overall_top1']:.3f}",
            f"  auto-taggable rate    {m['auto_taggable_rate']:.3f}",
            f"  accuracy on autotag   {m['accuracy_on_autotagged']:.3f}",
            f"  teacher time saved    {m['teacher_time_saved']:.3f}",
            f"  routed to triage      {int(m['n_routed_to_triage'])}",
        ]
    )
