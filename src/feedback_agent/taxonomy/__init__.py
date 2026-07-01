"""Misconception taxonomy: load Eedi's misconception_mapping.csv + retrieval.

Eedi ships ``misconception_mapping.csv`` (MisconceptionId -> MisconceptionName),
which IS the expert taxonomy. ``load_mapping`` reads it. The retrieval seam lives
in ``retrieval.py`` (Day 3): ``build_retriever`` returns an in-context retriever
for small taxonomies and a sentence-transformers + Chroma one for large ones.

``candidates_for`` is a convenience wrapper for the in-context path. Unlike the
Day-1 version it is **blind to the gold label** (no gold-peeking), so eval numbers
reflect real retrieval, not a rigged candidate list.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..models import DiagnosisItem
from .retrieval import (
    EmbeddingRetriever,
    InContextRetriever,
    Retriever,
    build_retriever,
)

__all__ = [
    "load_mapping",
    "candidates_for",
    "build_retriever",
    "Retriever",
    "InContextRetriever",
    "EmbeddingRetriever",
]


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
    """In-context candidates for an item (blind to the gold label).

    Convenience over ``InContextRetriever``: returns the taxonomy capped to
    ``limit`` (order-preserving, no gold-peeking). For real retrieval on a large
    taxonomy use ``build_retriever(...)`` / ``EmbeddingRetriever``.
    """
    return InContextRetriever(mapping).candidates(item, k=limit)


def _pick(columns, candidates: list[str]) -> str:
    lower = {c.lower(): c for c in columns}
    for cand in candidates:
        if cand in columns:
            return cand
        if cand.lower() in lower:
            return lower[cand.lower()]
    raise KeyError(f"none of {candidates} found in columns {list(columns)}")
