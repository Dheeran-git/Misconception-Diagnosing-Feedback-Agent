# ARCHITECTURE

The source of truth for *how* the system works. If you change the design, update
this file and add a line to the Decision Log in `STATUS.md`.

## Design principle

Two different agents live in this project; never conflate them:

- **Claude Code (Agent SDK)** = the *dev tool* building the repo, and the
  *runtime model access* for the product (via the Max plan credit).
- **The feedback agent** = the *product*: an explicit, readable orchestration we
  write on top of the SDK. The SDK provides model calls, tool use, hooks, and
  session state. **Our code makes the decisions** (when to escalate, how to score
  confidence) so a human can explain every step to a judge.

## The loop (state machine)

```
            ┌─────────────┐
  answer ─► │   ASSESS     │  MCQ math item + chosen answer → correct? (FR1)
            └──────┬──────┘
                   │ correct ──────────────► DONE (high confidence)
                   │ wrong (chose a distractor)
                   ▼
            ┌─────────────┐
            │  DIAGNOSE   │  tag the misconception behind the distractor;
            └──────┬──────┘  matched vs Eedi gold for eval (FR2)
                   ▼
            ┌─────────────┐
            │  REMEDIATE  │  targeted Socratic hint, no answer reveal (FR3)
            └──────┬──────┘
                   ▼  (follow-up attempt: simulated learner or next item)
            ┌─────────────┐
            │   VERIFY    │  resolved? compare new attempt to misconception (FR4)
            └──────┬──────┘
              ┌────┴────┐
       resolved│         │not resolved
              ▼          ▼
            DONE      ┌─────────────┐
                      │  ESCALATE   │  stronger hint / new representation;
                      └──────┬──────┘  agent decides; capped at N escalations
                             └────► back to VERIFY, or hand to teacher queue
```

Confidence is computed at ASSESS/DIAGNOSE (and re-checked after VERIFY). Below
threshold → push to the **teacher tagging-triage queue** instead of
auto-finalizing (FR5). The spine dataset is **Eedi** (math MCQ + gold
misconception labels); see the Datasets note below and `EVAL.md`.

## Modules

- `agent.py` — orchestrates the state machine above. Holds the escalation cap,
  the transitions, and the routing-to-triage decision. This is the file a judge
  will ask about — keep it legible.
- `grading.py` — **assess** step: given an MCQ math item + the student's chosen
  answer, determine correctness and build the context for diagnosis; parses to a
  Pydantic `AssessResult`. (Rubric-aware free-response grading lives here too, but
  only for the optional ASAP-SAS stretch — see `EVAL.md`.)
- `diagnosis.py` — retrieves candidate misconceptions for the item/topic, asks the
  model to pick the best-fit with evidence; returns `Diagnosis(label, evidence, confidence)`.
  Predictions are matched against Eedi gold `MisconceptionId` in the eval.
- `remediation.py` — generates the Socratic intervention for a given misconception;
  guardrail check that it doesn't leak the final answer.
- `confidence.py` — self-consistency: sample the diagnosis k times (or low-temp
  variants), measure agreement, map to a confidence score + triage decision.
- `tools/math_check.py` — SymPy tool exposed to the agent: parse both expressions,
  test symbolic/numeric equivalence; returns a structured result.
- `taxonomy/` — the misconception taxonomy. **Seed it from Eedi's
  `misconception_mapping.csv` (MisconceptionId → name)** — that's a ready-made
  expert taxonomy. Start scoped to one Construct/Subject + the retrieval seam
  (sentence-transformers + Chroma, or in-context if small).
- `state.py` — SQLite. Tables: `attempts`, `triage_queue`, `grade_cache`. Cache
  key = hash(answer + rubric + prompt_version + model).
- `prompts/` — versioned prompt templates. Bump version on change; it's part of
  the cache key.

## Agent SDK integration (verify exact API at the docs)

Use the Agent SDK's:
- **structured query / tool use** for grading and diagnosis calls;
- **custom tool** registration to expose `math_check` to the agent;
- **hooks** (pre/post tool-use, session start/end, stop) to log the full trace to
  a file — this is the demo footage and the debugger;
- **session resume** to carry student state across attempts in the verify/escalate
  loop.

Authentication is via the Claude Code CLI on the Max plan (no API key). Confirm
current function names, option fields, and hook names here before coding against
them: https://code.claude.com/docs/en/agent-sdk/overview
Do not trust SDK signatures from blog posts; the official page is canonical.

## Data contracts (Pydantic — sketch, refine in code)

```python
class AssessResult(BaseModel):
    is_correct: bool
    chosen_answer: str            # the distractor the student selected
    confidence: float             # filled by confidence.py
    # optional (ASAP free-response stretch only):
    rubric_score: float | None = None
    per_criterion: dict[str, float] | None = None

class Diagnosis(BaseModel):
    misconception_id: str | None  # None if no clear misconception
    label: str
    evidence: str
    confidence: float

class Intervention(BaseModel):
    text: str                     # Socratic; no final answer
    targets_misconception_id: str
    escalation_level: int
```

## Datasets (spine + stretch — full detail in EVAL.md)

- **Spine — Eedi "Mining Misconceptions in Mathematics" (Kaggle, NeurIPS 2024).**
  Math MCQs with expert-labeled misconceptions behind each wrong-answer distractor;
  ships `misconception_mapping.csv` (your taxonomy). Powers the ASSESS/DIAGNOSE
  steps and the headline metric. Note: ~60% of the original test misconceptions
  were *unseen* in training — design the held-out split to mirror that.
- **Optional stretch — ASAP-SAS (Kaggle).** Science/English free-response, QWK
  agreement. Only if Day 6 has slack, to show the grader generalizes to
  free-response. Not core; do not let it split the demo narrative.

## Model tiering (conserve credit)

- Bulk **assess** (correctness check): fast Claude model.
- **Diagnosis** (the reasoning-heavy step): stronger model.
- **Remediation/verify**: fast model is usually fine; measure before upgrading.
- Confirm current model identifiers in the docs; do not hardcode guesses.

## Why not a framework (LangChain/LangGraph)

The loop is the differentiator and the thing judges probe. We keep the
orchestration as explicit Python so it's fully explainable and debuggable. The
Agent SDK already gives us tool use + hooks + sessions; a heavier framework adds
magic we'd have to understand under time pressure. Decision logged in STATUS.

## Optional novelty flourish: active diagnosis

A single, scripted demo path where — given ambiguity between two candidate
misconceptions — the agent selects the next problem that best disambiguates them
(optimal-experiment-design flavor) and visibly zeroes in. Built **after** the safe
loop works, isolated so it can be cut without affecting any metric.
