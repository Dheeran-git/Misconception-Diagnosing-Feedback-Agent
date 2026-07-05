"""Baseline misconception diagnosis (cache-aware).

Day 1: a **single-shot** diagnoser. Given a gradable item + candidate
misconceptions, return a ``Diagnosis``. No retrieval (candidates come from the
taxonomy seam), no remediation, no verify/escalate — those are later days.

Caching lives here so both the harness and (later) the product loop benefit:
we check SQLite before ever calling the model.
"""
from __future__ import annotations

import sqlite3

from . import config, state
from .models import Diagnosis, DiagnosisItem
from .prompts import DIAGNOSE_PROMPT_VERSION, load_prompt
from .sdk_client import diagnose_call


def diagnose_baseline(
    item: DiagnosisItem,
    candidates: list[tuple[str, str]],
    *,
    conn: sqlite3.Connection | None = None,
    model: str | None = None,
    force_offline: bool = False,
    use_cache: bool = True,
    variant: str = "",
) -> tuple[Diagnosis, str]:
    """Return (Diagnosis, mode). mode is 'live', 'offline', or 'cache'.

    Reads the SQLite diagnosis cache first; on a miss, calls the model seam and
    writes the result back. Pass ``conn`` to reuse a connection across a run.
    ``variant`` tags self-consistency samples so they cache independently.
    """
    model = model or config.DIAGNOSIS_MODEL
    candidate_ids = [cid for cid, _ in candidates]
    key = state.cache_key(
        item.question_id, item.chosen_answer, candidate_ids, DIAGNOSE_PROMPT_VERSION, model, variant
    )

    own_conn = conn is None
    if conn is None:
        conn = state.connect()
    try:
        if use_cache:
            cached = state.get_cached(conn, key)
            if cached is not None:
                return cached, "cache"

        template = load_prompt(DIAGNOSE_PROMPT_VERSION)
        diagnosis, mode = diagnose_call(
            item, candidates, model=model, template=template, force_offline=force_offline
        )
        if use_cache:
            state.set_cached(
                conn,
                key,
                question_id=item.question_id,
                model=model,
                prompt_version=DIAGNOSE_PROMPT_VERSION,
                mode=mode,
                diagnosis=diagnosis,
            )
        return diagnosis, mode
    finally:
        if own_conn:
            conn.close()
