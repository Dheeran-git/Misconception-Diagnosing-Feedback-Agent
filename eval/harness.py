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

from feedback_agent import config, state
from feedback_agent.diagnosis import diagnose_baseline
from feedback_agent.models import DiagnosisItem
from feedback_agent.taxonomy import Retriever, build_retriever

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
    retriever: Retriever | None = None,
    k: int | None = None,
    split_name: str = "",
) -> RunResult:
    """Diagnose each item and score. Retrieval narrows the taxonomy to top-k
    candidates (blind to gold); ``recall@k`` reports how often the gold survives.
    """
    own_conn = conn is None
    if conn is None:
        conn = state.connect()
    if retriever is None:
        retriever = build_retriever(mapping)
    k = k if k is not None else config.RETRIEVAL_K

    preds: list[str | None] = []
    ranked_lists: list[list[str]] = []
    candidate_id_lists: list[list[str]] = []
    gold: list[str] = []
    modes: Counter = Counter()
    records: list[dict] = []

    try:
        for item in items:
            candidates = retriever.candidates(item, k=k)
            candidate_ids = [cid for cid, _ in candidates]
            diagnosis, mode = diagnose_baseline(
                item, candidates, conn=conn, force_offline=force_offline
            )
            preds.append(diagnosis.misconception_id)
            ranked_lists.append(diagnosis.ranked_misconception_ids)
            candidate_id_lists.append(candidate_ids)
            gold.append(item.gold_misconception_id)
            modes[mode] += 1
            records.append(
                {
                    "question_id": item.question_id,
                    "gold": item.gold_misconception_id,
                    "pred": diagnosis.misconception_id,
                    "correct": diagnosis.misconception_id == item.gold_misconception_id,
                    "retrieved": item.gold_misconception_id in candidate_ids,
                    "mode": mode,
                }
            )
    finally:
        if own_conn:
            conn.close()

    summary = M.summarize(preds, ranked_lists, gold, k=k)
    summary[f"recall@{k}"] = M.recall_at_k(candidate_id_lists, gold)
    _ = split_name  # reserved for labeled reporting
    return RunResult(metrics=summary, modes=modes, records=records)
