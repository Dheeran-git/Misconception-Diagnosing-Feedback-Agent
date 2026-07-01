"""Versioned prompt templates.

Prompts live in files (never inline in logic) so they are diffable IP and so the
version string can be part of the cache key. Bump the version whenever the text
of the corresponding prompt file changes.
"""
from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent

# The active diagnosis prompt. Bump this (and add a new file) on any edit to the
# prompt body — it is part of the SQLite cache key. v2 (Day 3) adds explicit
# work-backwards reasoning + a generic worked example.
DIAGNOSE_PROMPT_VERSION = "diagnose_v2"


def load_prompt(version: str) -> str:
    """Return the raw template text for a prompt version (e.g. 'diagnose_v1')."""
    path = PROMPTS_DIR / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt template not found: {path}")
    return path.read_text(encoding="utf-8")
