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

# Remediation prompts (Day 4). The two arms of the efficacy experiment.
REMEDIATE_TARGETED_VERSION = "remediate_targeted_v1"
REMEDIATE_GENERIC_VERSION = "remediate_generic_v1"

# Simulated-learner prompt (Day 4).
LEARNER_PROMPT_VERSION = "learner_v1"

# Rubric-aware free-response grader (FR10 optional stretch — ASAP-SAS).
GRADE_FREE_RESPONSE_VERSION = "grade_free_response_v1"


def load_prompt(version: str) -> str:
    """Return the raw template text for a prompt version (e.g. 'diagnose_v1')."""
    path = PROMPTS_DIR / f"{version}.md"
    if not path.exists():
        raise FileNotFoundError(f"prompt template not found: {path}")
    return path.read_text(encoding="utf-8")
