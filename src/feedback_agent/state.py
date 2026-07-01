"""SQLite persistence: diagnosis cache (Day 1) + attempts/triage schemas (later).

The cache is the credit-conservation mechanism (Prime Directive #5): a graded
diagnosis is keyed by a hash of everything that could change the answer, so
re-running the eval reads from disk instead of re-spending the Agent SDK credit.

Cache key = sha256(question_id + chosen_answer + sorted(candidate_ids) +
prompt_version + model). Prompt version and model are included because changing
either changes the output — see prompts/__init__.py.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from . import config
from .models import Diagnosis

_SCHEMA = """
CREATE TABLE IF NOT EXISTS diagnosis_cache (
    cache_key   TEXT PRIMARY KEY,
    question_id TEXT NOT NULL,
    model       TEXT NOT NULL,
    prompt_ver  TEXT NOT NULL,
    mode        TEXT NOT NULL,          -- 'live' or 'offline'
    diagnosis   TEXT NOT NULL,          -- JSON of Diagnosis
    created_at  TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Used from Day 4+; created now so the schema is stable.
CREATE TABLE IF NOT EXISTS attempts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id   TEXT NOT NULL,
    chosen_answer TEXT,
    step          TEXT,                 -- assess/diagnose/remediate/verify/escalate
    payload       TEXT,                 -- JSON
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS triage_queue (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id   TEXT NOT NULL,
    diagnosis     TEXT,                 -- JSON
    confidence    REAL,
    resolved      INTEGER DEFAULT 0,
    created_at    TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def cache_key(
    question_id: str,
    chosen_answer: str,
    candidate_ids: list[str],
    prompt_version: str,
    model: str,
) -> str:
    payload = "|".join(
        [question_id, chosen_answer, ",".join(sorted(candidate_ids)), prompt_version, model]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open (creating parent dirs + schema) the SQLite DB."""
    path = Path(db_path) if db_path is not None else config.DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.executescript(_SCHEMA)
    return conn


def get_cached(conn: sqlite3.Connection, key: str) -> Diagnosis | None:
    row = conn.execute(
        "SELECT diagnosis FROM diagnosis_cache WHERE cache_key = ?", (key,)
    ).fetchone()
    if row is None:
        return None
    return Diagnosis.model_validate(json.loads(row[0]))


def set_cached(
    conn: sqlite3.Connection,
    key: str,
    *,
    question_id: str,
    model: str,
    prompt_version: str,
    mode: str,
    diagnosis: Diagnosis,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO diagnosis_cache "
        "(cache_key, question_id, model, prompt_ver, mode, diagnosis) VALUES (?, ?, ?, ?, ?, ?)",
        (key, question_id, model, prompt_version, mode, diagnosis.model_dump_json()),
    )
    conn.commit()
