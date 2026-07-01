"""Runtime config, read from the environment with defaults matching .env.example.

No new dependency: values come from ``os.getenv`` with sane defaults. Run with
``uv run --env-file .env ...`` (or export the vars) to override. Keeping this in
one module means the cache key, DB path, and model tier all have a single source
of truth.
"""
from __future__ import annotations

import os
from pathlib import Path

# Repo root = two levels up from this file (src/feedback_agent/config.py).
REPO_ROOT = Path(__file__).resolve().parents[2]


def _get(name: str, default: str) -> str:
    return os.getenv(name, default)


# --- App config (mirrors .env.example) ---
TRIAGE_CONFIDENCE_THRESHOLD: float = float(_get("TRIAGE_CONFIDENCE_THRESHOLD", "0.7"))
SELF_CONSISTENCY_K: int = int(_get("SELF_CONSISTENCY_K", "5"))
MAX_ESCALATIONS: int = int(_get("MAX_ESCALATIONS", "2"))
TOPIC: str = _get("TOPIC", "linear_equations")

# SQLite path (relative paths resolved against the repo root so the DB lands in
# the gitignored data/ dir regardless of CWD).
_db = _get("DB_PATH", "data/cache.sqlite")
DB_PATH: Path = Path(_db) if os.path.isabs(_db) else REPO_ROOT / _db

# --- Model tiering (ARCHITECTURE.md: fast for bulk, stronger for reasoning) ---
# Overridable via env so we never hardcode a single guess. Diagnosis is the
# reasoning-heavy step; bulk assess (later) uses the fast tier.
DIAGNOSIS_MODEL: str = _get("DIAGNOSIS_MODEL", "claude-opus-4-8")
FAST_MODEL: str = _get("FAST_MODEL", "claude-haiku-4-5-20251001")

# --- Offline switch: when set, never call the live SDK (deterministic + free). ---
OFFLINE: bool = _get("FEEDBACK_AGENT_OFFLINE", "0").lower() in {"1", "true", "yes"}

# --- Retrieval (Day 3) ---
# 'auto' picks in-context for a small taxonomy, embeddings for a large one.
RETRIEVER: str = _get("RETRIEVER", "auto")          # auto | incontext | embedding
# Taxonomies at or below this size fit in context; above it we embed + retrieve.
RETRIEVAL_INCONTEXT_MAX: int = int(_get("RETRIEVAL_INCONTEXT_MAX", "200"))
RETRIEVAL_K: int = int(_get("RETRIEVAL_K", "25"))   # candidates fed to the diagnoser
EMBED_MODEL: str = _get("EMBED_MODEL", "all-MiniLM-L6-v2")
# Persistent Chroma dir (gitignored). None -> ephemeral in-memory client.
CHROMA_DIR: Path = REPO_ROOT / ".chroma"

# Where real Eedi data lives (gitignored); harness falls back to eval/fixtures/.
DATA_DIR: Path = REPO_ROOT / "data"
FIXTURES_DIR: Path = REPO_ROOT / "eval" / "fixtures"
