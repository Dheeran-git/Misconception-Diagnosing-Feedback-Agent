"""FR5 CONFIDENCE: self-consistency over k diagnosis samples → calibrated score.

We diagnose the same item k times, each with the candidate list in a different
(deterministically shuffled) order — a temperature-free perturbation the SDK
supports. Agreement among the k top-1 picks is the confidence: if the model lands
on the same misconception regardless of ordering, we trust it; if it flips, we
don't. Below ``TRIAGE_CONFIDENCE_THRESHOLD`` the diagnosis is routed to the
teacher tagging-review queue instead of being auto-finalized.

Each sample caches under a distinct ``variant`` so re-runs are free and the k
calls don't collapse to one cached answer.
"""
from __future__ import annotations

import random
import sqlite3
from collections import Counter

from . import config, state
from .diagnosis import diagnose_baseline
from .models import Diagnosis, DiagnosisItem


def agreement_confidence(top_picks: list[str | None]) -> float:
    """Fraction of samples that agree with the modal (most common) top-1 pick."""
    if not top_picks:
        return 0.0
    modal, count = Counter(top_picks).most_common(1)[0]
    return count / len(top_picks)


def _shuffled(candidates: list[tuple[str, str]], seed: int) -> list[tuple[str, str]]:
    out = list(candidates)
    random.Random(seed).shuffle(out)
    return out


def diagnose_with_confidence(
    item: DiagnosisItem,
    candidates: list[tuple[str, str]],
    *,
    k: int | None = None,
    conn: sqlite3.Connection | None = None,
    model: str | None = None,
    force_offline: bool = False,
) -> tuple[Diagnosis, list[str | None]]:
    """Diagnose k times over shuffled candidate orders; return the modal diagnosis
    with ``confidence`` filled in, plus the raw k top-1 picks (for auditing)."""
    k = k or config.SELF_CONSISTENCY_K
    own_conn = conn is None
    if conn is None:
        conn = state.connect()
    try:
        diags: list[Diagnosis] = []
        for i in range(k):
            perturbed = _shuffled(candidates, seed=i)
            d, _ = diagnose_baseline(
                item, perturbed, conn=conn, model=model,
                force_offline=force_offline, variant=f"sc{i}",
            )
            diags.append(d)
    finally:
        if own_conn:
            conn.close()

    picks = [d.misconception_id for d in diags]
    conf = agreement_confidence(picks)
    modal = Counter(picks).most_common(1)[0][0]
    # final = a sample whose top-1 is the modal pick (keeps its evidence/ranking)
    final = next((d for d in diags if d.misconception_id == modal), diags[0])
    final = final.model_copy(update={"confidence": conf})
    return final, picks


def should_triage(confidence: float, threshold: float | None = None) -> bool:
    """Route to the teacher queue when confidence is below threshold."""
    threshold = config.TRIAGE_CONFIDENCE_THRESHOLD if threshold is None else threshold
    return confidence < threshold
