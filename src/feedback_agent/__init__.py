"""feedback_agent — misconception-diagnosing feedback agent for MCQ math.

Day 1 surface: models, config, SQLite cache/state, taxonomy loader, and a
baseline single-shot diagnoser. The full diagnose->remediate->verify->escalate
loop is built later (see PLAN.md); this package intentionally exposes only the
pieces the eval harness needs today.
"""

__all__ = ["config", "models", "state", "diagnosis", "sdk_client"]
