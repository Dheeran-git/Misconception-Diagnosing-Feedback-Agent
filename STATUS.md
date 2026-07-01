# STATUS — Living Tracker

> Update this at the end of every session. Keep it short and current. Claude Code:
> reflect real state here, not aspirations.

**Current day:** Day 1 (eval harness first)
**Last updated:** 2026-07-01
**Core-complete (Day 4 loop runs end-to-end)?** ❌ not yet (Day 1 harness only)

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

## Current metrics (fill as they exist; "—" until measured)

> ⚠️ Numbers below are on the **synthetic fixture** (8 questions / 6 invented
> misconceptions), NOT real Eedi. They validate the pipeline, they are **not**
> reportable quality metrics. Real numbers require the real Eedi CSVs in `data/`.

| Metric | Value | Split | Date |
|---|---|---|---|
| Misconception diagnosis accuracy — top-1 (PRIMARY) | 0.333 (dev) / 0.000 (heldout-unseen) | fixture, live Opus 4.8 | 2026-07-01 |
| Misconception MAP@k (k=25) | 0.558 (dev) / 0.321 (heldout-unseen) | fixture, live Opus 4.8 | 2026-07-01 |
| — offline-stub baseline (pipeline smoke) | top1 0.00 / MAP@25 0.35 | dev (fixture) | 2026-07-01 |
| % auto-taggable @ threshold | — | | |
| Teacher tagging time saved (headline) | — | | |
| Remediation efficacy (targeted vs generic) | — | | |
| QWK on ASAP free-response (optional stretch) | — | | |

## In progress

- Nothing mid-flight. Live baseline over the fixture is done and cached; the
  generalization gap (top-1 0.333 dev → 0.000 on held-out **unseen**
  misconceptions) is visible and on-narrative for the integrity story.

## Next up

- Day 2: rubric-aware grading + confirm cache behavior on real data.
- When Eedi CSVs arrive: drop `train.csv` + `misconception_mapping.csv` into
  `data/`, re-run `pytest` / harness — loader auto-prefers `data/`.

## Blockers

- **Eedi dataset not yet in the environment** (no Kaggle CLI/creds). Using the
  EVAL.md-sanctioned synthetic fixture in the meantime. Not blocking the harness.

## Decision Log (append-only; one line each, newest first)

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
- [ ] Live loop shown end-to-end on one example
- [ ] Teacher triage view shown
- [ ] README documents how every number is computed
- [ ] AI-use disclosure added if rules require it
- [ ] Submitted before deadline
