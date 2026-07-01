"""Run the baseline diagnoser over a set of items and compute the metrics table.

Cache-first: each item goes through ``diagnose_baseline`` (SQLite-cached), so a
re-run reads from disk instead of re-spending credit. Returns the metrics dict,
a per-mode counter (cache/live/offline), and the raw per-item records for
inspection / hand-verification.
"""
from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass, field

from feedback_agent import state
from feedback_agent.diagnosis import diagnose_baseline
from feedback_agent.models import DiagnosisItem
from feedback_agent.taxonomy import candidates_for

from . import metrics as M


@dataclass
class RunResult:
    metrics: dict[str, float]
    modes: Counter = field(default_factory=Counter)
    records: list[dict] = field(default_factory=list)


def run(
    items: list[DiagnosisItem],
    mapping: dict[str, str],
    *,
    conn: sqlite3.Connection | None = None,
    force_offline: bool = False,
    candidate_limit: int | None = None,
    k: int = 25,
    split_name: str = "",
) -> RunResult:
    own_conn = conn is None
    if conn is None:
        conn = state.connect()

    preds: list[str | None] = []
    ranked_lists: list[list[str]] = []
    gold: list[str] = []
    modes: Counter = Counter()
    records: list[dict] = []

    try:
        for item in items:
            candidates = candidates_for(item, mapping, limit=candidate_limit)
            diagnosis, mode = diagnose_baseline(
                item, candidates, conn=conn, force_offline=force_offline
            )
            preds.append(diagnosis.misconception_id)
            ranked_lists.append(diagnosis.ranked_misconception_ids)
            gold.append(item.gold_misconception_id)
            modes[mode] += 1
            records.append(
                {
                    "question_id": item.question_id,
                    "gold": item.gold_misconception_id,
                    "pred": diagnosis.misconception_id,
                    "correct": diagnosis.misconception_id == item.gold_misconception_id,
                    "mode": mode,
                }
            )
    finally:
        if own_conn:
            conn.close()

    summary = M.summarize(preds, ranked_lists, gold, k=k)
    _ = split_name  # reserved for labeled reporting
    return RunResult(metrics=summary, modes=modes, records=records)
