# CLAUDE.md — Project Constitution

> This file is read automatically by Claude Code. Treat it as the standing
> orders for every session. If a request conflicts with this file, stop and
> flag the conflict instead of silently complying.

## Mission (one sentence)

Build a **misconception-diagnosing feedback agent** for multiple-choice math
items that doesn't just mark an answer wrong — it figures out *why* the student is
wrong (names the specific misconception, scored against expert gold labels),
generates a targeted Socratic intervention, verifies whether the fix worked, and
escalates on its own when it didn't. Spine dataset: **Eedi — Mining Misconceptions
in Mathematics** (see `EVAL.md`).

This is a hackathon entry for **EdTech 3.0**, Track 2 (Assessment & Feedback
Automation). Build window: **June 18–25, 2026**. Submission: June 25, 23:59 UTC.

## Read these first

- `PRD.md` — what we're building and why; the judging criteria as requirements.
- `ARCHITECTURE.md` — the technical design and the agent loop. Source of truth for *how*.
- `PLAN.md` — the 7-day execution order. Source of truth for *when*.
- `EVAL.md` — how we measure, and the integrity rules for our numbers.
- `STATUS.md` — living state. **Update it at the end of every session.**

## Prime Directives (do not violate)

1. **Eval-first.** The eval harness is built on Day 1, before the product. Every
   change is measured against it. We never claim a result we haven't measured.
2. **Core working by Day 4.** The full loop (diagnose → intervene → verify →
   escalate) must run end-to-end and produce a real metric by end of Day 4.
   Everything after Day 4 is polish on a working system, not new construction.
3. **No scope creep.** This week, the answer to "should I add this feature?" is
   almost always **no**. Finishing beats cleverness. If unsure, ask the human.
4. **Own the code.** The human must be able to explain, cold, how escalation
   decides and how every headline number is computed. Write the agent loop and
   eval methodology to be *read by a human*, not just to run. No magic.
5. **Conserve the credit.** Programmatic model calls run on the Max plan's
   monthly Agent SDK credit (see Cost Discipline). Cache aggressively; keep the
   eval set small. Never re-spend on an answer we've already graded.

## Architecture in one breath

`assess MCQ answer (correct?) → if wrong: diagnose the specific misconception
behind the chosen distractor (vs Eedi gold) → generate targeted Socratic
intervention → follow-up attempt → verify misconception resolved → escalate
autonomously if not → emit calibrated confidence → route low-confidence diagnoses
to the teacher tagging-review queue.`

Full detail and the state machine live in `ARCHITECTURE.md`. Do not redesign the
loop without updating that file and the Decision Log in `STATUS.md`.

## Tech stack (locked)

- **Language:** Python 3.11+, end to end. No JavaScript.
- **Model access:** **Claude Agent SDK**, authenticated through the Claude Code
  CLI on the Max plan — **no `ANTHROPIC_API_KEY`, no Anthropic API account.**
  Usage draws on the plan's monthly Agent SDK credit, not the interactive coding
  budget. Confirm the exact current SDK API (function names, options, hooks,
  session resume) at the official docs before relying on signatures:
  https://code.claude.com/docs/en/agent-sdk/overview
  Do **not** copy SDK call signatures from blog posts — verify against that page.
- **Math verification tool:** SymPy (agent calls it to check algebraic equivalence).
- **Retrieval:** sentence-transformers + Chroma (local, no server) over the
  misconception taxonomy. If the taxonomy is small enough to fit in context, an
  in-context lookup is acceptable — but keep the retrieval seam in place.
- **Eval:** pandas + scikit-learn, run as `pytest`. QWK via
  `sklearn.metrics.cohen_kappa_score(weights="quadratic")`.
- **State / cache / triage queue:** SQLite (file-based, no server).
- **UI:** Streamlit (teacher triage view + student feedback view). Do not build
  a Next.js/React frontend — it is not worth the hours.
- **Env/deps:** uv. Lint with ruff. Validate all structured model output with
  Pydantic models.

## Repo layout

```
src/feedback_agent/   # the product (importable library — NOT a CLI-only script)
  agent.py            # the diagnose→intervene→verify→escalate orchestration
  grading.py          # rubric-aware grading pass
  diagnosis.py        # misconception diagnosis
  remediation.py      # targeted Socratic intervention generation
  confidence.py       # self-consistency scoring + triage routing
  tools/math_check.py # SymPy equivalence tool exposed to the agent
  taxonomy/           # misconception taxonomy + retrieval
  state.py            # SQLite: attempts, triage queue, grade cache
  prompts/            # versioned prompt templates (the real IP — keep in git)
eval/
  harness.py          # run the agent over a dataset
  metrics.py          # QWK, misconception accuracy, % auto-gradable, time-saved
  simulated_learner.py# LLM student instantiated with a known misconception
  test_eval.py        # pytest: thresholds as regression tests
app/dashboard.py      # Streamlit
data/                 # datasets + cache.sqlite (gitignored)
```

The eval harness and the Streamlit app both **import the same agent module**.
No HTTP layer between them. Add FastAPI only if a real reason appears (it won't, this week).

## Cost discipline (the human does these once, Day 0 — remind them if not done)

- **Claim the Agent SDK monthly credit** in Claude plan settings (it is NOT on by
  default; one-time opt-in).
- **Leave "extra usage" / usage credits DISABLED**, so requests hard-stop at the
  credit ceiling instead of billing pay-as-you-go overage. No surprise charges.
- Authenticate Claude Code with the **Max plan only** (`claude login`). If an
  `ANTHROPIC_API_KEY` env var is set, Claude Code/SDK will use that and bill the
  API instead — make sure it is unset.
- Keep the eval set to ~150–300 examples. Cache every graded result in SQLite,
  keyed by a hash of (answer + rubric + prompt version), so re-runs read from disk.
- Bulk grading on a fast Claude model; reserve the stronger reasoning model for
  the diagnosis step only. Confirm current model names in the docs.

## Working agreement for Claude Code

- **Before large changes**, propose the approach (plan mode) and wait for a yes.
  Don't one-shot the whole agent loop.
- **Commit at every working milestone** with a clear message. A working state we
  can roll back to is the safety net for a solo 7-day build.
- **At the end of each session**, update `STATUS.md`: what changed, current
  metrics, what's next, any new decision in the Decision Log.
- **Ask before** adding a dependency, adding a feature not in `PRD.md`, or
  changing the architecture or the eval methodology.
- **Keep prompts in `src/feedback_agent/prompts/` as versioned files**, never
  inline buried in logic. The prompt version is part of the cache key.
- **Log the full agent trace** (each diagnose/verify/escalate step + tool calls)
  to a file via SDK hooks. It's both the debugger and the demo footage.

## Integrity rules (these protect the only thing that wins: real numbers)

- Maintain a **held-out test split the agent never sees during iteration.** Tune
  on dev, report on held-out.
- **Never tune prompts to specific eval examples** to make a number go up. That's
  overfitting and it makes the headline metric fake.
- Hand-verify a handful of grades against gold labels so we know the harness
  itself is correct before trusting it.
- Datasets: **Eedi (spine, required)** for misconception labels; **ASAP-SAS
  (optional stretch)** for free-response QWK. **Confirm current access and license
  before building on them.** See `EVAL.md`.

## Deployment-story caveat (don't architect into a wall)

This runs under the human's own Max plan. Anthropic's Agent SDK terms do not
allow offering claude.ai login / plan rate limits to third-party end users
without approval. So pitch it as **a pilot the operator runs**, not "every
teacher logs in with their own Claude account." This changes nothing in the
build — only how we describe the deployment in the writeup.
