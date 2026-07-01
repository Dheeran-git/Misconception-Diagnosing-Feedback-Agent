# Misconception-Diagnosing Feedback Agent

EdTech 3.0 · Track 2 (Assessment & Feedback Automation) · solo build.

A feedback agent for multiple-choice math items that doesn't just mark an answer
wrong — it **diagnoses the specific misconception behind the chosen distractor
(scored against expert gold labels), generates a targeted Socratic intervention,
verifies whether it worked, and escalates on its own when it didn't.**
Low-confidence diagnoses route to a teacher tagging-review queue. Spine dataset:
**Eedi — Mining Misconceptions in Mathematics**.

> Most graders tell a student they're wrong. This one figures out *why*, does
> something about it, and checks whether it worked.

## Docs (read in this order)

1. `CLAUDE.md` — operating rules for the build (Claude Code reads this automatically).
2. `PRD.md` — what we're building and why; judging criteria as requirements.
3. `ARCHITECTURE.md` — the agent loop and technical design.
4. `PLAN.md` — the 7-day execution order.
5. `EVAL.md` — how we measure and the integrity rules.
6. `STATUS.md` — current state (kept live).

## Model access — important

This project does **not** use an Anthropic API key. The product's model calls run
on the **Claude Agent SDK authenticated through the Max plan**, drawing on the
plan's monthly Agent SDK credit (separate from interactive Claude Code usage).

Before anything else (Day 0):

1. Claim the Agent SDK monthly credit in your Claude plan settings (one-time opt-in).
2. Disable "extra usage" / usage credits so requests hard-stop at the ceiling
   instead of billing overage.
3. `claude login` with your Max plan; make sure `ANTHROPIC_API_KEY` is **unset**
   (if set, the SDK uses the API and bills pay-as-you-go instead).
4. Confirm the current SDK API at https://code.claude.com/docs/en/agent-sdk/overview

## Setup

```bash
uv init
uv add claude-agent-sdk sympy pydantic pandas scikit-learn \
       sentence-transformers chromadb streamlit
uv add --dev ruff pytest
git init && git add . && git commit -m "scaffold: project docs + plan"
```

(Confirm the exact Agent SDK package name in the docs above.)

## Run

```bash
# Evaluation (also the dev loop): runs the agent over the dataset, prints metrics
pytest eval/test_eval.py

# Dashboards
streamlit run app/dashboard.py
```

## Layout

```
src/feedback_agent/  product (importable library)
eval/                harness, metrics, simulated learner, pytest gates
app/                 Streamlit teacher + student views
data/                datasets + cache.sqlite (gitignored)
```

## Stack

Python 3.11+ · Claude Agent SDK (Max plan) · SymPy · sentence-transformers +
Chroma · pandas + scikit-learn · SQLite · Streamlit · uv · ruff · pytest.

## Status

See `STATUS.md`. Core loop target: end-to-end and measured by **end of Day 4**.
