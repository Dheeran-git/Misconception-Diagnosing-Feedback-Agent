# STATUS — Living Tracker

> Update this at the end of every session. Keep it short and current. Claude Code:
> reflect real state here, not aspirations.

**Current day:** Day 7 (writeup + demo)
**Last updated:** 2026-07-01
**Core-complete (Day 4 loop runs end-to-end)?** ✅ YES — assess→diagnose→remediate→verify→escalate→triage runs end-to-end (offline-deterministic + live seam)

## Day-0 checklist

- [x] Agent SDK works headless on this machine (`smoke_test.py` → GREEN)
- [x] `ANTHROPIC_API_KEY` unset (SDK uses subscription OAuth)
- [x] uv project + core deps installed (`pyproject.toml`, `uv.lock`)
- [x] git initialized, committed
- [x] Agent SDK Python API confirmed against docs + installed pkg (v0.2.110):
      `query()` + `ClaudeAgentOptions(output_format={"type":"json_schema",...})`
      → `ResultMessage.structured_output`
- [ ] Dataset access: **Eedi** not yet provided. Loader targets the real Eedi
      schema; running on a **synthetic fixture** (`eval/fixtures/`) until the real
      CSVs are dropped into `data/`.

## Day-1 deliverables (this session)

- [x] `eval/dataset.py` — Eedi loader (real schema) that explodes each question
      into one diagnosis instance per labeled wrong distractor.
- [x] Held-out split holding some misconceptions out **entirely** (unseen),
      fixed seed=13 (`unseen_misconception_split`).
- [x] `eval/metrics.py` — top-1 accuracy + MAP@25.
- [x] Baseline single-shot diagnoser (`src/feedback_agent/diagnosis.py`) with an
      **offline deterministic stub** and a **live Agent SDK** path (same seam).
- [x] SQLite diagnosis cache (`src/feedback_agent/state.py`), key =
      sha256(question_id + chosen_answer + sorted(candidate_ids) + prompt_version
      + model). Re-runs read from disk.
- [x] `eval/test_eval.py` — 7 pytest gates (loader, unseen split, metric math,
      baseline runs, **cache-hit on re-run**). All green, offline & deterministic.

## Day-2 deliverables (this session)

- [x] `src/feedback_agent/grading.py` — FR1 ASSESS step for MCQ →
      `AssessResult` (deterministic option-letter correctness, confidence 1.0),
      plus an `answers_equivalent` seam where the Day-4 SymPy tool plugs in.
- [x] `grade_cache` table + `get_grade`/`set_grade` and `assess_cached`
      (cache-hit on re-run), and `attempts` logging (`log_attempt`, FR7) in
      `state.py`.
- [x] `qwk()` (quadratic-weighted kappa) added to `eval/metrics.py`, ready for
      the *optional* ASAP free-response stretch — not run on the MCQ spine.
- [x] Tests: 11 green (7 Day-1 + 4 Day-2: assess correctness, cache-hit+log,
      assess-vs-item, QWK). Lint clean.

**Deviation from PLAN.md Day 2 (logged below):** PLAN's literal Day-2 DoD
("rubric-aware grading, QWK improves over baseline") is the ASAP free-response
stretch, which the Decision Log already demoted to optional. On the Eedi MCQ
spine, ASSESS is deterministic (no QWK to move), so Day 2 built the on-spine
ASSESS step + grade cache instead. QWK scaffolding is in place for the stretch.

## Day-3 deliverables (this session)

- [x] Retrieval seam (`src/feedback_agent/taxonomy/retrieval.py`): `Retriever`
      protocol + `InContextRetriever` (small taxonomy) + `EmbeddingRetriever`
      (sentence-transformers + Chroma, the locked stack). `build_retriever` auto-
      selects by taxonomy size (`RETRIEVAL_INCONTEXT_MAX`, default 200).
- [x] **Embedding retriever validated** (real model): on a noised 14-item
      taxonomy it retrieves top-6 by cosine, the gold misconception survives, and
      unrelated-topic misconceptions are filtered out. This is the scalability
      path for real Eedi (~2.5k misconceptions). Chroma fed vectors directly, so
      no Chroma-side model download (their CDN is 403 here).
- [x] Retrieval is **blind to the gold label** (removed Day-1 gold-peeking);
      `recall@k` metric added (`eval/metrics.py`) to report the retrieval ceiling.
- [x] Diagnosis prompt **v2** (`prompts/diagnose_v2.md`): explicit work-backwards
      reasoning (a misconception must *reproduce* the chosen distractor) + one
      generic worked example (NOT from the fixture — no teaching-to-the-test).
      Prompt version bump invalidates the v1 cache by design.
- [x] Harness builds the retriever once and reports `recall@k`. Tests: 15 green +
      1 gated embedding test (run with `FEEDBACK_AGENT_RUN_EMBED=1`). Lint clean.

## Day-4 deliverables (this session) — CORE COMPLETE

- [x] `agent.py` — explicit state machine assess→diagnose→remediate→verify→
      escalate→triage. Escalation capped at `MAX_ESCALATIONS`; unresolved cases
      route to the teacher triage queue. Every step logged (attempts, FR7) and
      returned as a trace (FR9).
- [x] `remediation.py` — targeted vs generic Socratic interventions + a
      **no-answer-leak guardrail** (`leaks_answer`): a leaking live generation is
      regenerated once, then falls back to a safe templated hint. Offline stub
      never leaks.
- [x] `eval/simulated_learner.py` — LLM student instantiated with a known
      misconception (offline stub + live seam); answers free-form, verified via
      `answers_equivalent`.
- [x] `eval/efficacy.py` — remediation-efficacy experiment (targeted vs generic
      resolution rate + gap). Triage queue helpers in `state.py`.
- [x] Tests: 20 green + 1 gated. Loop resolve/escalate/triage paths, guardrail
      edge cases, and the efficacy gap all covered. Lint clean.

## Day-5 deliverables (this session)

- [x] `confidence.py` — self-consistency: diagnose k times over
      deterministically-shuffled candidate orders (temperature-free perturbation
      the SDK supports), agreement among top-1 picks = confidence. Each sample
      caches under a distinct `variant` so re-runs are free.
- [x] `should_triage(confidence, threshold)` + batch tagging pipeline
      (`eval/tagging.py`): auto-finalize confident tags, route the rest to the
      teacher triage queue (FR5). Produces % auto-taggable + teacher-time-saved.
- [x] `auto_taggable_summary` metric (`eval/metrics.py`): auto-taggable rate,
      accuracy-on-autotagged (the quality bar), teacher-time-saved.
- [x] Tests: 24 green + 1 gated (agreement math, triage threshold, auto-taggable
      math, k-sample confidence, tagging pipeline). Lint clean.

## Day-6 deliverables (this session)

- [x] `app/dashboard.py` — thin Streamlit app, **imports the same agent modules
      as the eval harness** (no HTTP layer). Two views:
  - **Student feedback:** pick a question+answer → assess → diagnose → targeted
    Socratic hint (with the guardrail flag), no answer revealed.
  - **Teacher triage:** the low-confidence queue from SQLite, most-uncertain
    first, with confidence flags 🔴/🟢, predicted misconception + evidence.
  - Sidebar "offline (fast)" toggle to demo without spending credit.
- [x] Verified: launches headless and serves HTTP 200; pure helpers unit-tested
      offline (25 tests green). Lint clean.
- [ ] Optional active-diagnosis flourish: **cut** (PLAN.md says cut if it risks
      the demo; not worth the hours vs. finishing).

## Day-7 deliverables (this session)

- [x] `README.md` rewritten as the writeup: leads with the metrics table + **how
      each number is computed**, the held-out unseen split, the honest calibration
      failure mode, exact reproduce commands, a 2–3 min demo runbook, and an
      **AI-use disclosure**.
- [ ] Record the 2–3 min demo video (human — headline number in first 10s, live
      loop on one example, teacher triage view).
- [ ] Drop real Eedi CSVs into `data/` to convert fixture numbers → reportable
      Eedi numbers (human — needs Kaggle access).

## Current metrics (fill as they exist; "—" until measured)

> ⚠️ Numbers below are on the **synthetic fixture** (8 questions / 6 invented
> misconceptions), NOT real Eedi. They validate the pipeline, they are **not**
> reportable quality metrics. Real numbers require the real Eedi CSVs in `data/`.
> Note: prompt v1→v2 barely moved on the fixture (MAP +0.03 dev, −0.02 held) —
> expected, since 8 synthetic items is statistical noise for a prompt change. The
> v2 reasoning prompt and retrieval are evaluated for real on Eedi, not here.
> Efficacy caveat: the live gap is n=2/arm on the synthetic fixture with a single
> hint — directional, not statistical. The methodology (live learner reasons
> about hint content, resolution well-defined vs a known misconception) is what
> generalizes; the full-size number comes from running it on real Eedi.
> **Confidence FAILURE MODE (honest):** on the 6 one-per-misconception items
> (which include held-out *unseen* misconceptions — the hardest subset), the
> diagnoser scored top-1 0.167, and at threshold 0.7 it auto-tagged exactly one
> item — which was WRONG (accuracy-on-autotagged 0.000). So self-consistency
> confidence is *miscalibrated* here: one confidently-wrong case slipped the
> filter while 5/6 uncertain cases were correctly routed to triage. Causes: k=3
> gives coarse confidence (only 0.33/0.67/1.0); synthetic n=6 on the unseen slice.
> The triage *mechanism* is sound; calibration + a tuned threshold need real Eedi.
> We are NOT reporting a teacher-time-saved "win" from this.

| Metric | Value | Split | Date |
|---|---|---|---|
| Misconception diagnosis accuracy — top-1 (PRIMARY) | v2: 0.333 dev / 0.000 held (v1 identical) | fixture, live Opus 4.8 | 2026-07-01 |
| Misconception MAP@k (k=25) | v2: 0.590 dev / 0.300 held (v1: 0.558 / 0.321) | fixture, live Opus 4.8 | 2026-07-01 |
| Retrieval recall@k (retrieval ceiling) | 1.000 (in-context, small taxonomy); embedding path validated | fixture | 2026-07-01 |
| — offline-stub baseline (pipeline smoke) | top1 0.00 / MAP@25 0.35 | dev (fixture) | 2026-07-01 |
| % auto-taggable @ threshold | 0.167 (1/6) @ conf≥0.7, k=3 | fixture, live | 2026-07-01 |
| accuracy on auto-tagged slice | **0.000** (the 1 auto-tagged item was wrong — miscalibration, see note) | fixture, live | 2026-07-01 |
| Teacher tagging time saved (headline) | 0.167 mechanically (5/6 correctly routed to triage) — NOT a clean win on this hard subset | fixture, live | 2026-07-01 |
| Remediation efficacy (targeted vs generic) | **live gap +1.000** (targeted 2/2 resolved, generic 0/2, both triaged; n=2/arm, 1 hint) · offline mechanism gap 1.000 | fixture (live learner) | 2026-07-01 |
| QWK on ASAP free-response (optional stretch) | — | | |

## In progress

- Nothing mid-flight. Live baseline over the fixture is done and cached; the
  generalization gap (top-1 0.333 dev → 0.000 on held-out **unseen**
  misconceptions) is visible and on-narrative for the integrity story.

## Next up

- **Day 7:** demo (2–3 min, headline number first 10s), writeup/README leading
  with metrics + how each is computed (held-out split, unseen handling), AI-use
  disclosure if required. Stop building.
- When Eedi CSVs arrive: drop `train.csv` + `misconception_mapping.csv` into
  `data/`, re-run `pytest` / harness — loader auto-prefers `data/`. On the real
  ~2.5k taxonomy, `build_retriever` auto-switches to the embedding path.

## Blockers

- **Eedi dataset not yet in the environment** (no Kaggle CLI/creds). Using the
  EVAL.md-sanctioned synthetic fixture in the meantime. Not blocking the harness.

## Decision Log (append-only; one line each, newest first)

- _2026-07-01_ — Day 7: README rewritten as the writeup (metrics-first, how each
  number is computed, honest calibration failure mode, reproduce commands, demo
  runbook, AI-use disclosure). Remaining items are human-only: record the video
  and drop real Eedi CSVs into `data/`. Per PLAN, stop building.
- _2026-07-01_ — Day 6: thin Streamlit dashboard (teacher triage + student
  feedback), importing the agent library directly (no HTTP). Pure data helpers
  split out for unit-testing; rendering guarded under `__main__`. Active-diagnosis
  flourish cut (scope discipline; finishing > cleverness).
- _2026-07-01_ — Day 5: confidence via self-consistency over k *candidate-order-
  shuffled* diagnosis samples (the SDK exposes no temperature knob, so we perturb
  ordering instead). Confidence-based triage lives in the batch tagging pipeline
  (`eval/tagging.py`, FR5's natural home), separate from the remediation loop.
  % auto-taggable and teacher-time-saved derive from the confidence threshold.
- _2026-07-01_ — Day 4 (CORE COMPLETE): explicit `agent.py` state machine (no
  framework). Verify = simulated learner re-attempts and answers correctly;
  escalate = new hint at a higher level, capped at `MAX_ESCALATIONS`; unresolved
  → teacher triage. Answer-leak guardrail on remediation. Simulated learner
  answers free-form (checked via `answers_equivalent`) so it needs no option list.
  Offline efficacy gap is a mechanism check (stub resolves on any targeted hint);
  the reported gap comes from the live learner.
- _2026-07-01_ — Day 3: retrieval seam = `InContextRetriever` (small taxonomy) +
  `EmbeddingRetriever` (sentence-transformers + Chroma), auto-selected by size.
  Retrieval made **blind to gold** (dropped Day-1 gold-peeking) + added `recall@k`
  so numbers reflect real retrieval. Diagnosis prompt bumped to v2 (work-backwards
  reasoning + generic example). Fixture (6 misconceptions) can't show retrieval
  narrowing, so the embedding path was validated on a noised synthetic taxonomy.
- _2026-07-01_ — Day 2 built the on-spine **ASSESS** step (MCQ correctness →
  `AssessResult`) + grade cache + attempts log, NOT PLAN.md's literal "rubric
  grading + QWK". Reason: QWK/rubric grading is free-response (ASAP), already
  demoted to optional stretch; MCQ assess is deterministic so there is no QWK to
  improve. QWK metric scaffolded in `eval/metrics.py` for the stretch.
- _2026-07-01_ — Day 1: eval harness first (Prime Directive #1). Baseline diagnoser
  is single-shot, no retrieval yet (taxonomy candidate seam returns full list;
  Chroma retrieval deferred to Day 3). Offline stub + live SDK seam so pytest is
  deterministic/free; live path verified GREEN on this machine.
- _2026-07-01_ — No Kaggle access here → build loader to the real Eedi schema +
  run on a small labeled **synthetic fixture** (EVAL.md fallback). Fixture numbers
  are pipeline smoke only, never reported as Eedi results. Same loader swaps to
  real CSVs in `data/` with no code change.
- _YYYY-MM-DD_ — Spine dataset = Eedi (math MCQ + gold misconceptions). Headline metric = misconception diagnosis accuracy / MAP@k (not QWK). ASAP-SAS demoted to optional free-response stretch. Reason: verified neither dataset is math free-response w/ misconception labels; Eedi gives gold labels that directly measure the differentiator.
- _YYYY-MM-DD_ — Model access = Claude Agent SDK on Max plan credit; no API key.
- _YYYY-MM-DD_ — Track 2 chosen (solo, no live users, ML strength → measurable on benchmarks).
- _YYYY-MM-DD_ — No orchestration framework; explicit Python loop for explainability.
- _YYYY-MM-DD_ — Domain = math (machine-verifiable misconceptions); one Construct/Subject first.

## Demo readiness (Day 7 gate)

- [ ] Headline number lands in first 10s of video
- [x] Live loop runs end-to-end on one example (needs the demo UI on Day 6)
- [x] Teacher triage view shown (Streamlit; serves headless, reads live queue)
- [x] README documents how every number is computed (+ reproduce commands)
- [x] AI-use disclosure added
- [ ] Submitted before deadline
