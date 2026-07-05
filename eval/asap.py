"""FR10 (optional stretch): ASAP-SAS free-response grading + QWK.

Shows the grader generalizes beyond MCQ math to rubric-scored short-answer
responses in another domain. Targets the real ASAP-SAS schema (Kaggle):

  train.tsv columns: Id, EssaySet, Score1, Score2, EssayText

Per-essay-set rubrics ship separately in ASAP; we keep them in a small JSON meta
file (question + rubric + max_score keyed by EssaySet). Real data goes in
``data/asap/`` (train.tsv + meta.json); tests fall back to the committed synthetic
fixture (SAME schema, clearly not real ASAP — the number is a pipeline check).

QWK (quadratic-weighted Cohen's kappa) is ASAP's standard agreement metric,
computed human ``Score1`` vs the model's score (``eval/metrics.py::qwk``).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from feedback_agent import config
from feedback_agent.grading import grade_free_response

from .metrics import qwk


@dataclass
class AsapItem:
    id: str
    essay_set: str
    human_score: int
    answer: str
    question: str
    rubric: str
    max_score: int


def _resolve() -> tuple[Path, Path]:
    real_csv = config.DATA_DIR / "asap" / "train.tsv"
    real_meta = config.DATA_DIR / "asap" / "meta.json"
    if real_csv.exists() and real_meta.exists():
        return real_csv, real_meta
    return config.FIXTURES_DIR / "asap_sample.csv", config.FIXTURES_DIR / "asap_meta.json"


def load_asap(csv: Path | None = None, meta: Path | None = None) -> list[AsapItem]:
    csv_path, meta_path = (csv, meta) if csv and meta else _resolve()
    sep = "\t" if str(csv_path).endswith(".tsv") else ","
    df = pd.read_csv(csv_path, sep=sep, dtype=str).fillna("")
    meta_map = json.loads(Path(meta_path).read_text(encoding="utf-8"))

    items: list[AsapItem] = []
    for _, r in df.iterrows():
        es = str(r["EssaySet"])
        m = meta_map.get(es, {})
        items.append(
            AsapItem(
                id=str(r["Id"]),
                essay_set=es,
                human_score=int(float(r["Score1"])),
                answer=str(r["EssayText"]),
                question=str(m.get("question", "")),
                rubric=str(m.get("rubric", "")),
                max_score=int(m.get("max_score", 3)),
            )
        )
    return items


def run_asap_grading(
    items: list[AsapItem], *, force_offline: bool = False, model: str | None = None
) -> dict:
    human: list[int] = []
    model_scores: list[int] = []
    records: list[dict] = []
    for it in items:
        grade, mode = grade_free_response(
            it.question, it.rubric, it.answer,
            max_score=it.max_score, model=model, force_offline=force_offline,
        )
        human.append(it.human_score)
        model_scores.append(grade.score)
        records.append(
            {"id": it.id, "human": it.human_score, "model": grade.score, "mode": mode}
        )
    return {
        "n": len(items),
        "qwk": qwk(human, model_scores) if len(items) > 1 else 0.0,
        "human": human,
        "model": model_scores,
        "records": records,
    }
