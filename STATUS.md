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

## Gap-closing pass (post-Day-7)

Closed the four buildable gaps from the PRD audit:

- [x] **FR6 SymPy math tool** — `tools/math_check.py`: `math_equivalent`
      (symbolic/numeric/string) now backs `grading.answers_equivalent`, so ASSESS
      and VERIFY use SymPy, not string compare ("1/2"=="0.5", "2x+3"=="3+2x").
      Also exposed as an SDK custom tool; **verified live** that the agent calls
      `mcp__math__math_check` and returns the right answer.
- [x] **FR9 trace via SDK hooks** — `trace.py::TraceLogger` writes every loop step
      to `traces/<run_id>.jsonl`; a PreToolUse SDK hook logs each live tool call to
      the same trace (**verified live** on the math tool). Wired into `agent.py`.
- [x] **Confidence in the loop** — `run_loop(with_confidence=True)` runs
      self-consistency and routes low-confidence diagnoses to triage (FR5) inside
      the loop, not just the batch tagger.
- [x] **Dashboard metrics panel** — teacher view now shows queue size / distinct
      questions / low-confidence count.
- [x] Tests: 28 green + 1 gated (added SymPy equivalence, trace JSONL, loop
      trace+low-confidence-triage). Lint clean.

- [x] **FR10 ASAP-SAS free-response stretch** — `grading.grade_free_response`
      (rubric-aware, 0–max_score, stub + live seam) + `eval/asap.py` loader (real
      ASAP schema, synthetic fixture fallback) + **QWK** (quadratic-weighted
      kappa) over human Score1 vs model score. Shows the grader generalizes beyond
      MCQ math to another domain.

- [x] **Hand-verify vs gold (integrity)** — spot-checked 10 random real Eedi
      items: all 10 gold misconceptions correctly match the specific chosen
      distractor (e.g. `4/11+7/11→11/22` = "adds numerators and denominators";
      `0.7²→0.14` = "mixes up squaring and doubling"). The harness data join is
      correct.

Still open: real ASAP `train_rel_2.tsv` (responses) for QWK — not provided;
demo video (human).

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

> ✅ **REAL Eedi numbers (n=60/split, self-consistency k=3 — supersedes n=25).**
> 1. **Retrieval is the bottleneck.** recall@25 ≈ 0.50 → the off-the-shelf MiniLM
>    retriever surfaces the gold in the top-25 (of 2,587) ~half the time;
>    diagnosis-given-retrieval is ~0.81 dev / 0.71 held. The reasoning step is
>    strong; the lever is a fine-tuned retriever/reranker.
> 2. **Confidence is calibrated, but modestly.** Auto-tagged (conf≥0.7) accuracy
>    beats overall on both splits (0.581 vs 0.417 dev; 0.439 vs 0.333 held) — so
>    confidence helps, but far less than the noisy n=25 (0.706 vs 0.48) implied. At
>    conf 0.7 you auto-tag ~70% at only ~44–58% accuracy; raise the threshold to
>    hold an expert bar. (Scaling n=25→60 is exactly what corrected the optimism —
>    the earlier synthetic n=6 "miscalibration" and rosy n=25 were both artifacts.)
> Unseen gap (top-1 0.42→0.33) is real and expected. n=60/split is solid but not
> final; 150–300 (`python -m eval.benchmark`) tightens it further. Older
> n=25/n=20/fixture rows kept for provenance.
> Note: prompt v1→v2 barely moved on the fixture (MAP +0.03 dev, −0.02 held) —
> expected, since 8 synthetic items is statistical noise for a prompt change. The
> v2 reasoning prompt and retrieval are evaluated for real on Eedi, not here.
> Efficacy caveat: the live gap is n=2/arm on the synthetic fixture with a single
> hint — directional, not statistical. The methodology (live learner reasons
> about hint content, resolution well-defined vs a known misconception) is what
> generalizes; the full-size number comes from running it on real Eedi.
> **Confidence calibration — small-sample scare, resolved on real data.** An
> early *synthetic* n=6 run auto-tagged 1 item and it was wrong (acc 0.000), which
> looked like miscalibration. On **real Eedi (n=25/split)** confidence is in fact
> calibrated: auto-tagged accuracy **0.706 dev / 0.643 held vs 0.48/0.40 overall**.
> The n=6 result was a small-sample artifact — kept as an honest reminder of why
> tiny synthetic slices don't back headline claims.

| Metric | Value | Split | Date |
|---|---|---|---|
| **Misconception diagnosis top-1 (PRIMARY) — REAL Eedi** | **0.417 dev / 0.333 held-out unseen** (n=60/split, k=3) | REAL Eedi, live Opus 4.8 + MiniLM retrieval | 2026-07-01 |
| **Misconception MAP@25 — REAL Eedi** | **0.450 dev / 0.394 held-out unseen** (n=60/split) | REAL Eedi, live | 2026-07-01 |
| Retrieval recall@25 (the bottleneck) — REAL Eedi | 0.517 dev / 0.467 held (top-25 of 2,587, off-the-shelf MiniLM) | REAL Eedi | 2026-07-01 |
| — earlier noisier samples (superseded) | n=25/split k=3: 0.48/0.40; n=20 single-shot: 0.45/0.30; fixture 0.33 | — | 2026-07-01 |
| — offline-stub baseline (pipeline smoke) | top1 0.00 / MAP@25 0.35 | dev (fixture) | 2026-07-01 |
| % auto-taggable @ conf≥0.7 — REAL Eedi | **0.717 dev / 0.683 held** (n=60/split, k=3) | REAL Eedi, live | 2026-07-01 |
| accuracy on auto-tagged slice — REAL Eedi | **0.581 dev / 0.439 held** vs 0.417/0.333 overall → modest but real calibration (raise threshold to hold a higher bar) | REAL Eedi, live | 2026-07-01 |
| Teacher tagging time saved (headline) — REAL Eedi | ~72% dev / 68% held auto-tagged, but only at ~44–58% accuracy @ conf 0.7 — tune the threshold for an expert bar | REAL Eedi, live | 2026-07-01 |
| Remediation efficacy (targeted vs generic) | **live gap +1.000** (targeted 2/2, generic 0/2; n=2/arm) — re-confirmed genuinely live after the max_turns fix | fixture (live learner) | 2026-07-01 |
| QWK on ASAP-SAS free-response (stretch) — REAL | **pooled 0.599 (n=80); mean-per-set 0.357** (8/set × 10 sets, zero-shot Haiku, generic rubrics) | REAL ASAP-SAS, live | 2026-07-01 |

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

## Blockers / data status

- **Have (real, in `data/`, gitignored):** full Eedi dataset
  (`train.csv` 4,370 labeled instances + `misconception_mapping.csv` 2,587
  misconceptions) → **real diagnosis numbers measured**; `data/asap/meta.json`
  (real ASAP rubrics/prompts for all 10 sets).
- **Have (real):** full ASAP-SAS `train_rel_2.tsv` (17,043 responses, 10 sets) at
  `data/asap/train.tsv` + real rubrics in `data/asap/meta.json` → **real QWK
  measured**.
- **To finalize submission numbers:** scale the Eedi benchmark to n=150–300/split
  and the ASAP QWK to more per set (this session: Eedi n=25/split, ASAP 8/set —
  both indicative). All data is now in place; just costs credit/time.

## Decision Log (append-only; one line each, newest first)

- _2026-07-01_ — **Scaled Eedi benchmark (n=60/split, k=3)** supersedes n=25. top-1
  0.417 dev / 0.333 held; MAP@25 0.450 / 0.394; recall@25 0.517 / 0.467;
  auto-taggable 0.72 / 0.68 at auto-tagged accuracy 0.581 / 0.439 (vs 0.417/0.333
  overall). Scaling corrected the optimistic n=25: calibration is real but modest
  (raise threshold for an expert bar); retrieval bottleneck confirmed. Honest read.
- _2026-07-01_ — **Real ASAP-SAS QWK measured.** Full `train_rel_2.tsv` (17,043
  responses / 10 sets) wired; rebuilt `meta.json` with real per-set rubric scoring
  guides from the description docs. Zero-shot Haiku grader, 8/set: pooled QWK
  0.599 (n=80), mean-per-set 0.357 (dragged by set 8's −0.39 on n=8). Shows the
  grader generalizes to free-response; small per-set n is noisy.
- _2026-07-01_ — **Real Eedi, full benchmark (n=25/split, k=3).** top-1 0.480 dev /
  0.400 held; MAP@25 0.480 / 0.428; recall@25 0.520 / 0.480; auto-taggable 0.68 /
  0.56 with auto-tagged accuracy 0.706 / 0.643 (vs 0.48/0.40 overall). Two
  findings: retrieval is the bottleneck (off-the-shelf MiniLM), and confidence IS
  calibrated on real data (revises the synthetic-n=6 miscalibration scare). Added
  reproducible `eval/benchmark.py`; hand-verified 10 items vs gold (10/10).
- _2026-07-01_ — **Real Eedi first measure (n=20 single-shot):** top-1 0.450 /
  0.300; superseded by the k=3 benchmark above. Fixed a float-id loader bug.
- _2026-07-01_ — **Bug fix + integrity re-measure:** the live structured-output
  calls used `max_turns=1`, which `output_format` can exceed → silent offline-stub
  fallback. This meant the free-response grader and the live remediation/simulated-
  learner calls (behind the efficacy number) ran as *stub*, not live. Fixed
  (`max_turns=6`) and re-ran: ASAP QWK is genuinely live 1.000 (n=10 synthetic);
  efficacy gap re-confirmed +1.000 genuinely live. Diagnosis path was unaffected.
- _2026-07-01_ — FR10 stretch: rubric-aware free-response grader + ASAP QWK
  (generalization beyond MCQ), synthetic fixture on the real ASAP schema.
- _2026-07-01_ — Gap-closing: FR6 SymPy tool (agent calls it live), FR9 trace via
  SDK hooks, confidence routing inside the loop, dashboard metrics panel.
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
