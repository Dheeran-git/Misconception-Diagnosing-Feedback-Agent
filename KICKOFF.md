# KICKOFF

## Day 0 — gate before you write any code (do these yourself)

1. `bash preflight.sh` → must end with **PASSED**.
2. `python smoke_test.py` → must print **GREEN**.
3. Agent SDK monthly credit **claimed** and **"extra usage" disabled** in plan settings.
4. Eedi competition **rules accepted** on Kaggle and data downloaded into `data/`
   (`kaggle competitions download -c eedi-mining-misconceptions-in-mathematics`).

Do not start Day 1 until the smoke test is GREEN. If it fails, fixing model
access in isolation now is far cheaper than debugging it tangled into the harness.

## Day 1 — paste this verbatim into Claude Code (in the repo root)

> Read CLAUDE.md, PRD.md, ARCHITECTURE.md, PLAN.md, and EVAL.md in full before
> doing anything. Confirm by summarizing, in 5 bullets: the mission, the locked
> architecture, the primary metric, and the two Prime Directives you consider
> most important.
>
> We are on Day 1. Per PLAN.md, build the EVALUATION HARNESS FIRST. Do NOT build
> the product agent loop (diagnose/remediate/verify/escalate) yet.
>
> Scope for this session only:
> 1. `eval/` loader for the Eedi data in `data/`: parse each question, its options,
>    and the correct answer; join `misconception_mapping.csv` so every wrong-answer
>    distractor carries its gold MisconceptionId and name.
> 2. A held-out split that holds some misconceptions out entirely (unseen),
>    mirroring the real competition. Write down how the split is made.
> 3. `eval/metrics.py`: top-1 misconception diagnosis accuracy and MAP@k (k=25).
> 4. A BASELINE single-shot diagnoser: given (question, correct answer, chosen wrong
>    answer, candidate misconception list), ask the model once for the most likely
>    misconception. No remediation, no verify/escalate — baseline only.
> 5. `eval/test_eval.py` (pytest) that runs the baseline over a ~150–300 item sample
>    and prints a metrics table.
> 6. Wire the SQLite diagnosis cache (`state.py`) so re-runs read from disk and
>    don't re-spend the Agent SDK credit.
>
> Constraints:
> - Model access is the Claude Agent SDK on my Max plan; there is NO
>   ANTHROPIC_API_KEY. Confirm the current SDK API against
>   https://code.claude.com/docs/en/agent-sdk/python and return the diagnosis as a
>   validated Pydantic object using
>   https://code.claude.com/docs/en/agent-sdk/structured-outputs
> - Keep all prompts in `src/feedback_agent/prompts/` as versioned files; the
>   prompt version is part of the cache key.
> - Before writing code, show me your plan and the file list, and wait for my go.
> - When done: run the harness, report the baseline numbers, update STATUS.md
>   (metrics table + Decision Log), and commit with a clear message.
>
> Stop once the baseline number exists. Do not start the product loop.

## Day 2 onward

Each day, point Claude Code at the next day in PLAN.md and its definition of done.
Keep the rule: the full loop must run end-to-end and produce a real number by
**end of Day 4**; Days 5–7 are polish, not new construction.
