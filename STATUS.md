# STATUS — Living Tracker

> Update this at the end of every session. Keep it short and current. Claude Code:
> reflect real state here, not aspirations.

**Current day:** Day 0 (setup)
**Last updated:** _(fill in)_
**Core-complete (Day 4 loop runs end-to-end)?** ❌ not yet

## Day-0 checklist

- [ ] Agent SDK monthly credit claimed (plan settings)
- [ ] Extra usage / usage credits DISABLED
- [ ] `claude login` on Max plan; `ANTHROPIC_API_KEY` unset
- [ ] uv project + deps installed
- [ ] git initialized, first commit
- [ ] Agent SDK docs read; real API noted
- [ ] Dataset access confirmed: **Eedi** (required spine) — see EVAL.md; ASAP optional

## Current metrics (fill as they exist; "—" until measured)

| Metric | Value | Split | Date |
|---|---|---|---|
| Misconception diagnosis accuracy — top-1 (PRIMARY) | — | | |
| Misconception MAP@k (k≈25) | — | | |
| % auto-taggable @ threshold | — | | |
| Teacher tagging time saved (headline) | — | | |
| Remediation efficacy (targeted vs generic) | — | | |
| QWK on ASAP free-response (optional stretch) | — | | |

## In progress

- _(what you're building right now)_

## Next up

- _(the next concrete task)_

## Blockers

- _(anything stuck — dataset access, SDK auth, etc.)_

## Decision Log (append-only; one line each, newest first)

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
