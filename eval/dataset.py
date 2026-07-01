"""Eedi loader + held-out split.

Targets the **real Eedi "Mining Misconceptions in Mathematics" schema** (Kaggle):

  train.csv columns (per question):
    QuestionId, ConstructId, ConstructName, SubjectId, SubjectName,
    CorrectAnswer (a letter A/B/C/D),
    QuestionText,
    AnswerAText, AnswerBText, AnswerCText, AnswerDText,
    MisconceptionAId, MisconceptionBId, MisconceptionCId, MisconceptionDId
  misconception_mapping.csv columns:
    MisconceptionId, MisconceptionName

We **explode** each question into one ``DiagnosisItem`` per *wrong* option that
carries a (non-null) gold MisconceptionId — i.e. one gradable diagnosis instance
per labeled distractor.

Data location: real files are expected in ``data/`` (gitignored). For tests we
fall back to the committed synthetic fixture in ``eval/fixtures/`` — SAME schema,
so nothing changes when the real CSVs arrive.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from feedback_agent import config
from feedback_agent.models import DiagnosisItem

_OPTIONS = ["A", "B", "C", "D"]


def _clean_id(v) -> str:
    """Normalize a misconception id. Eedi's train.csv stores them as floats
    (because unlabeled cells make the column float), so '1672.0' must become
    '1672' to match the integer ids in misconception_mapping.csv."""
    s = str(v).strip()
    if not s or s.lower() in {"nan", "none"}:
        return ""
    try:
        return str(int(float(s)))
    except ValueError:
        return s


@dataclass
class Dataset:
    items: list[DiagnosisItem]
    mapping: dict[str, str]  # misconception_id -> name


def _resolve_paths(train: Path | None, mapping: Path | None) -> tuple[Path, Path]:
    """Prefer real data/ files; fall back to the synthetic fixture."""
    if train and mapping:
        return train, mapping
    real_train = config.DATA_DIR / "train.csv"
    real_map = config.DATA_DIR / "misconception_mapping.csv"
    if real_train.exists() and real_map.exists():
        return real_train, real_map
    return (
        config.FIXTURES_DIR / "eedi_train_sample.csv",
        config.FIXTURES_DIR / "misconception_mapping.csv",
    )


def load_dataset(train_csv: Path | None = None, mapping_csv: Path | None = None) -> Dataset:
    from feedback_agent.taxonomy import load_mapping

    train_path, mapping_path = _resolve_paths(train_csv, mapping_csv)
    mapping = load_mapping(mapping_path)
    df = pd.read_csv(train_path, dtype=str).fillna("")

    items: list[DiagnosisItem] = []
    for _, row in df.iterrows():
        correct = str(row["CorrectAnswer"]).strip().upper()
        correct_text = str(row.get(f"Answer{correct}Text", ""))
        for opt in _OPTIONS:
            if opt == correct:
                continue
            gold = _clean_id(row.get(f"Misconception{opt}Id", ""))
            if not gold:
                continue  # unlabeled distractor -> not a gradable instance
            items.append(
                DiagnosisItem(
                    question_id=f"{row['QuestionId']}_{opt}",
                    construct_name=str(row.get("ConstructName", "")),
                    subject_name=str(row.get("SubjectName", "")),
                    question_text=str(row["QuestionText"]),
                    correct_answer=correct,
                    correct_answer_text=correct_text,
                    chosen_answer=opt,
                    chosen_answer_text=str(row.get(f"Answer{opt}Text", "")),
                    gold_misconception_id=gold,
                )
            )
    return Dataset(items=items, mapping=mapping)


def unseen_misconception_split(
    dataset: Dataset,
    *,
    holdout_frac: float = 0.4,
    seed: int = 13,
) -> tuple[list[DiagnosisItem], list[DiagnosisItem]]:
    """Split into (dev, heldout) holding some misconceptions out *entirely*.

    Mirrors Eedi's realism note (~60% of test misconceptions were unseen in
    training): we choose a fraction of distinct misconception ids uniformly at
    random (fixed seed) and route **every** instance of those ids to the held-out
    set, so the held-out split contains misconceptions the agent never saw during
    dev iteration. Report on held-out; tune on dev.

    ``holdout_frac`` is the fraction of *distinct misconception ids* held out.
    Returns (dev_items, heldout_items).
    """
    ids = sorted({it.gold_misconception_id for it in dataset.items})
    rng = random.Random(seed)
    n_holdout = max(1, round(len(ids) * holdout_frac)) if ids else 0
    heldout_ids = set(rng.sample(ids, n_holdout)) if ids else set()

    dev = [it for it in dataset.items if it.gold_misconception_id not in heldout_ids]
    heldout = [it for it in dataset.items if it.gold_misconception_id in heldout_ids]
    return dev, heldout
