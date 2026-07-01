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

## The loop (this is the product)

```
ASSESS ─correct──────────────────────────────────► done
  │ wrong (chose a distractor)
  ▼
DIAGNOSE ─► REMEDIATE ─► learner re-attempts ─► VERIFY ─resolved─► done
  (misconception   (targeted Socratic hint,        │ not resolved
   vs Eedi gold)    no answer leak)                ▼
                                            ESCALATE (≤ N) ─► back to REMEDIATE
                                                   │ cap reached
                                                   ▼
                                            TEACHER TRIAGE QUEUE
```

Written as explicit Python (`src/feedback_agent/agent.py`) — no orchestration
framework — so every decision (when to escalate, when to route to triage) is
auditable. The ASSESS/VERIFY steps check answers with **SymPy** (a real tool the
agent calls, not LLM arithmetic — FR6), and every step is logged to
`traces/<run_id>.jsonl` via the loop and SDK tool-use hooks (FR9). Full design in
`ARCHITECTURE.md`.

## Status

Days 1–6 of the 7-day plan are complete: the full loop runs end-to-end, backed by
an eval harness built **first** (Prime Directive: eval before product). The
Streamlit dashboard (teacher triage + student feedback) serves both users.

> ✅ **Measured on real Eedi.** The headline numbers below are on the actual
> Kaggle dataset. The finding: **diagnosis is strong, retrieval is the
> bottleneck** — off-the-shelf embedding retrieval surfaces the gold misconception
> in the top-25 (of 2,587) only ~half the time, but *given* retrieval, diagnosis
> top-1 is ~90% on dev. Sample is n=20/split (indicative; run 150–300 for the
> final number). A synthetic fixture (`eval/fixtures/`) ships so the suite runs
> without the licensed data.

## Metrics — and exactly how each is computed

Numbers marked **REAL Eedi** are on the actual Kaggle dataset (2,587
misconceptions, 4,370 labeled distractors); n=20/split, single-shot, live Opus
4.8 diagnosis + off-the-shelf MiniLM retrieval — indicative, run 150–300 for the
final submission number.

| Metric (judging axis) | Value | How it's computed |
|---|---|---|
| **Misconception diagnosis top-1** (Impact / primary) | **REAL Eedi: 0.450 dev · 0.300 held-out *unseen*** | predicted top-1 misconception == Eedi gold `MisconceptionId`, over one instance per labeled wrong distractor (`eval/metrics.py::top1_accuracy`) |
| **MAP@25** (Eedi's own metric) | **REAL Eedi: 0.460 dev · 0.329 held-out** | mean 1/rank of the gold id in the ranked candidate list (`map_at_k`) |
| **Retrieval recall@25** (Scalability / **the bottleneck**) | **REAL Eedi: 0.500 dev · 0.450 held-out** | share of items whose gold survives the top-25 retrieved (of 2,587) — recall≈0.5 means diagnosis-given-retrieval is ~90% dev; retrieval is the lever (`recall_at_k`) |
| **Remediation efficacy gap** (Impact) | **+1.000** live (targeted 2/2 vs generic 0/2; n=2/arm) | resolution rate of targeted vs generic hints on a live simulated learner with a known misconception (`eval/efficacy.py`) |
| **% auto-taggable / teacher time saved** (Scalability / headline) | 0.167 @ conf≥0.7 — see failure mode | share with self-consistency confidence ≥ threshold (`eval/tagging.py`, `auto_taggable_summary`) |
| **QWK on ASAP free-response** (optional stretch) | live **1.000** (n=10 synthetic, clear-cut — not statistical) | quadratic-weighted kappa, human Score1 vs model rubric score (`eval/asap.py`, generalization beyond MCQ) |

### The bottleneck is retrieval, not diagnosis (real-Eedi finding)

recall@25 ≈ 0.50 on real Eedi means the off-the-shelf MiniLM retriever surfaces
the gold misconception in the top-25 (of 2,587) only about half the time — that
caps top-1 at ~0.50. But top-1 0.45 ÷ recall 0.50 ≈ **90% diagnosis accuracy when
the gold was retrieved** (dev). So the reasoning step is strong; the clear next
lever is a **fine-tuned retriever / reranker** (exactly what won the Eedi
competition), not the diagnosis prompt. The unseen-misconception gap (top-1
0.45→0.30 dev→held) is real and expected.

Confidence caveat (from an earlier synthetic run): self-consistency confidence
was miscalibrated on a tiny hard slice (k=3 is coarse; n=6). The triage mechanism
works (routes uncertain cases to the teacher); calibration needs a real-data
threshold sweep. See `STATUS.md`.

## Integrity (how we keep the numbers real)

- **Held-out split with unseen misconceptions.** `unseen_misconception_split`
  (fixed `seed=13`) holds a fraction of *distinct misconception ids* out
  **entirely**, mirroring Eedi's ~60%-unseen test set. Tune on dev, report on
  held-out. This is why the held-out numbers are (honestly) much lower.
- **Retrieval is blind to the gold label** — candidates come from similarity to
  the question only; `recall@k` reports the ceiling.
- **No teaching to the test** — the improved diagnosis prompt (`diagnose_v2`)
  uses a *generic* worked example, never a fixture item.
- **Everything reproducible from the harness** (below); prompt version + model +
  candidate set are baked into the SQLite cache key.

## Setup

```bash
uv sync                       # Python 3.11+; installs the locked deps
python smoke_test.py          # confirms the Agent SDK runs on your Max plan (no API key)
```

Model access is the **Claude Agent SDK on the Max plan** — no `ANTHROPIC_API_KEY`
(if set, it bills the API instead of your plan credit). See `.env.example`.

## Reproduce every number

```bash
# Pipeline + offline gates (deterministic, no credit): loader, unseen split,
# metric math, the full loop (resolve/escalate/triage), guardrail, confidence.
uv run pytest -q                       # 30 tests + 1 gated

# Validate the real embedding retriever (downloads all-MiniLM-L6-v2):
FEEDBACK_AGENT_RUN_EMBED=1 uv run pytest -q -k embedding

# Real Eedi headline numbers (needs data/train.csv; spends credit; cached+resumable):
uv run python -m eval.benchmark --n 50 --k 1     # top-1 / MAP@25 / recall@25
uv run python -m eval.benchmark --n 25 --k 3     # + confidence / % auto-taggable / time-saved

# Other live experiments:
#   efficacy gap    — eval/efficacy.py::run_efficacy
#   ASAP QWK        — eval/asap.py::run_asap_grading (needs data/asap/train.tsv)
```

## Run the app

```bash
uv run streamlit run app/dashboard.py
```

- **Student feedback view:** pick a question + answer → named misconception +
  evidence + a Socratic hint (guardrail-checked, no answer revealed).
- **Teacher triage view:** the low-confidence queue, most-uncertain first, with
  confidence flags. Sidebar "offline (fast)" toggle demos without spending credit.

## Swapping in real Eedi

```bash
kaggle competitions download -c eedi-mining-misconceptions-in-mathematics
# unzip train.csv + misconception_mapping.csv into ./data/ (gitignored)
uv run pytest -q     # eval/dataset.py auto-prefers data/ over the fixture
```

On the real ~2.5k-misconception taxonomy, `build_retriever` auto-switches from the
in-context path to the sentence-transformers + Chroma embedding retriever.

## 2–3 minute demo runbook

1. **Open with the headline framing** (first 10s): "most graders say *wrong*; this
   one says *why*, fixes it, and checks." State the primary metric = misconception
   diagnosis accuracy vs Eedi gold.
2. **Student view, live:** submit a wrong answer → show the named misconception +
   evidence → the Socratic hint (note: no answer revealed) → "verify/escalate".
3. **Teacher view:** show the triage queue with confidence flags — low-confidence
   diagnoses routed for review (the autonomy + trust story).
4. **Terminal:** `uv run pytest -q` — every number falls out of the harness; call
   out the held-out *unseen* split and the honest calibration failure mode.

## Repo layout

```
src/feedback_agent/  agent loop, grading, diagnosis, remediation, confidence,
                     taxonomy/retrieval, tools/math_check (SymPy), trace (JSONL),
                     state (SQLite), versioned prompts/
eval/                harness, metrics, dataset+split, simulated learner,
                     efficacy + tagging experiments, fixtures, pytest gates
app/dashboard.py     Streamlit teacher + student views (imports the agent library)
data/                real Eedi CSVs + cache.sqlite (gitignored)
traces/              per-run agent traces, *.jsonl (gitignored)
```

## AI-use disclosure

This project was built with **Claude Code** (Anthropic) as the development
assistant, and its runtime model calls use the **Claude Agent SDK** on the Max
plan (diagnosis, remediation, the simulated learner). All evaluation metrics are
produced by the code in `eval/` and reproducible via `pytest`; no numbers are
hand-authored. The misconception gold labels are Eedi's expert annotations.

## Deployment note

Runs under the operator's own Max plan. Anthropic's Agent SDK terms don't allow
offering claude.ai login to third-party end users without approval, so this is
pitched as **a pilot the operator runs**, not per-teacher logins — a framing
choice only; it changes nothing in the build.

## Docs

`CLAUDE.md` (operating rules) · `PRD.md` · `ARCHITECTURE.md` · `PLAN.md` ·
`EVAL.md` · `STATUS.md` (live state, decision log, all numbers + caveats).
