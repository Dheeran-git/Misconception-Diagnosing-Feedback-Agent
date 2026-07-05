"""Remediation-efficacy experiment (EVAL.md / PRD Educational Impact).

For each item, instantiate a simulated learner holding that item's gold
misconception and run the full agent loop under two arms:
  - 'targeted': the intervention addresses the diagnosed misconception;
  - 'generic':  topic-blind encouragement (control).
Measure the resolution rate of each arm. The gap (targeted − generic) is the
learning-outcome evidence, with no real students.

Offline (stub) numbers are a *mechanism* check (the stub resolves on any targeted
hint) — the reported efficacy number comes from the live simulated learner, which
reasons about the hint's content and so couples resolution to diagnosis quality.
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict

from feedback_agent import state
from feedback_agent.agent import run_loop
from feedback_agent.models import DiagnosisItem
from feedback_agent.taxonomy import build_retriever

from .simulated_learner import SimulatedLearner


def one_per_misconception(items: list[DiagnosisItem]) -> list[DiagnosisItem]:
    """Pick a single representative item per gold misconception (small live runs)."""
    seen: dict[str, DiagnosisItem] = {}
    for it in items:
        seen.setdefault(it.gold_misconception_id, it)
    return list(seen.values())


def run_efficacy(
    items: list[DiagnosisItem],
    mapping: dict[str, str],
    *,
    arms: tuple[str, ...] = ("targeted", "generic"),
    conn: sqlite3.Connection | None = None,
    force_offline: bool = False,
    retriever=None,
) -> dict:
    own_conn = conn is None
    if conn is None:
        conn = state.connect()
    if retriever is None:
        retriever = build_retriever(mapping)

    agg: dict[str, dict] = {a: defaultdict(float) for a in arms}
    try:
        for arm in arms:
            for item in items:
                learner = SimulatedLearner(
                    item.gold_misconception_id, mapping.get(item.gold_misconception_id, "")
                )
                res = run_loop(
                    item, learner, retriever, arm=arm, conn=conn, force_offline=force_offline
                )
                a = agg[arm]
                a["n"] += 1
                a["resolved"] += 1 if res.resolved else 0
                a["unaided_correct"] += 1 if res.unaided_correct else 0
                a["triaged"] += 1 if res.routed_to_triage else 0
                a["interventions"] += res.interventions_used
    finally:
        if own_conn:
            conn.close()

    out: dict = {}
    for arm in arms:
        a = agg[arm]
        n = a["n"] or 1
        out[arm] = {
            "n": int(a["n"]),
            "resolution_rate": a["resolved"] / n,
            "triage_rate": a["triaged"] / n,
            "avg_interventions": a["interventions"] / n,
            "unaided_correct": int(a["unaided_correct"]),
        }
    if "targeted" in out and "generic" in out:
        out["efficacy_gap"] = out["targeted"]["resolution_rate"] - out["generic"]["resolution_rate"]
    return out


def format_efficacy(result: dict) -> str:
    lines = ["=== Remediation efficacy (targeted vs generic) ==="]
    for arm in ("targeted", "generic"):
        if arm in result:
            r = result[arm]
            lines.append(
                f"  {arm:<9} n={r['n']:<3} resolved={r['resolution_rate']:.3f} "
                f"triaged={r['triage_rate']:.3f} avg_hints={r['avg_interventions']:.2f}"
            )
    if "efficacy_gap" in result:
        lines.append(f"  efficacy_gap (targeted - generic) = {result['efficacy_gap']:+.3f}")
    return "\n".join(lines)
