# PLAN — 7-Day Execution

Build window: **June 18–25, 2026**. Submission: June 25, 23:59 UTC.
Golden rule: **core loop works end-to-end by end of Day 4.** Days 5–7 are polish
on a working system, not new construction.

## Day 0 (before the 18th) — setup, ~1 hour

- [ ] Claim the **Agent SDK monthly credit** in Claude plan settings (one-time opt-in).
- [ ] **Disable "extra usage" / usage credits** (hard-stop, no overage billing).
- [ ] `claude login` with the **Max plan only**; ensure `ANTHROPIC_API_KEY` is unset.
- [ ] `uv` project init; install Agent SDK, sympy, pydantic, pandas, scikit-learn,
      sentence-transformers, chromadb, streamlit, ruff, pytest.
- [ ] `git init`, first commit with all the `.md` files.
- [ ] Read the Agent SDK overview docs; note the real API for query/tools/hooks/sessions.
- [ ] Verify dataset access (ASAP short-answer; Eedi misconceptions) — see EVAL.md.

## Day 1 — eval harness FIRST + baseline grader

- Pull dataset; build `eval/harness.py`, `eval/metrics.py`, `eval/test_eval.py`.
- Implement a dumb single-shot grader and run it through the harness.
- **DoD:** `pytest` prints a baseline QWK number on real data. Measuring works
  before the product exists.

## Day 2 — rubric-aware grading + cache

- `grading.py` with rubric autogen; Pydantic `GradeResult`.
- SQLite `grade_cache` wired in (`state.py`).
- **DoD:** QWK improves over baseline; re-running the eval hits cache, not the model.

## Day 3 — diagnosis

- Misconception taxonomy for ONE topic; retrieval seam; `diagnosis.py`.
- Add misconception-accuracy metric to the harness.
- **DoD:** measured diagnosis accuracy on labeled data; a real number in STATUS.

## Day 4 — remediation + verify/escalate + simulated learner (CORE COMPLETE)

- `remediation.py` (no-answer-leak guardrail), verify/escalate logic in `agent.py`,
  `eval/simulated_learner.py`.
- **DoD:** full loop runs end-to-end; remediation-efficacy experiment produces a
  number (targeted vs. generic). **Commit this as the safe, working baseline.**

## Day 5 — confidence + triage + scalability number

- `confidence.py` (self-consistency); triage queue in SQLite.
- Compute % auto-gradable at the agreement threshold → time-saved figure.
- **DoD:** all four scoring-axis numbers exist and are reproducible from `pytest`.

## Day 6 — Streamlit UX (thin, clean) + optional flourish

- `app/dashboard.py`: teacher triage view (queue, confidence flags, metrics) +
  student feedback view. Keep it legible; don't sink hours here.
- If time: the scripted active-diagnosis demo path. Cut if flaky.
- **DoD:** a teacher and a student can each use the tool in the browser.

## Day 7 — demo + writeup + buffer

- 2–3 min video; **headline number in first 10 seconds**; show the loop live.
- Writeup/README: lead with metrics; document how each number is computed.
- AI-use disclosure if required by the rules.
- **DoD:** submitted before the deadline with time to spare. Stop building.

## Time-management law for this week

Claude Code makes you faster. Spend the saved time on **finishing and the demo**,
never on new features. "Should I add X?" → default **no**. Scope creep is the
failure mode, not idea choice.
