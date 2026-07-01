"""Misconception taxonomy: load Eedi's misconception_mapping.csv + candidate seam.

Eedi ships ``misconception_mapping.csv`` (MisconceptionId -> MisconceptionName),
which IS the expert taxonomy. Day 1 keeps the retrieval **seam** but not real
retrieval: ``candidates_for`` returns the full taxonomy (optionally capped). Day 3
swaps the body for sentence-transformers + Chroma without changing this signature.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..models import DiagnosisItem


def load_mapping(path: Path) -> dict[str, str]:
    """Return {misconception_id: misconception_name} from a mapping CSV.

    Accepts the real Eedi columns (MisconceptionId, MisconceptionName).
    """
    df = pd.read_csv(path, dtype=str).fillna("")
    id_col = _pick(df.columns, ["MisconceptionId", "misconception_id", "id"])
    name_col = _pick(df.columns, ["MisconceptionName", "misconception_name", "name"])
    return {str(r[id_col]): str(r[name_col]) for _, r in df.iterrows()}


def candidates_for(
    item: DiagnosisItem,
    mapping: dict[str, str],
    *,
    limit: int | None = None,
) -> list[tuple[str, str]]:
    """Return candidate (id, name) pairs for an item.

    Day 1: the full taxonomy (retrieval seam is here but a no-op). The gold id is
    guaranteed present so scoring is well-defined. ``limit`` caps the list for
    large real taxonomies; the gold id is always retained.
    """
    items = list(mapping.items())
    if limit is not None and len(items) > limit:
        gold = item.gold_misconception_id
        kept = [(cid, name) for cid, name in items if cid != gold][: max(0, limit - 1)]
        if gold in mapping:
            kept.append((gold, mapping[gold]))
        return kept
    return items


def _pick(columns, candidates: list[str]) -> str:
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    raise KeyError(f"none of {candidates} found in columns {list(columns)}")
