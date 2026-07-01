# EVAL — Measurement & Integrity

The eval harness is the moat: it's both the dev loop and the submission evidence.
Build it Day 1. Never report a number it didn't produce.

## Datasets

### Spine: Eedi — Mining Misconceptions in Mathematics (Kaggle, NeurIPS 2024)

`kaggle.com/competitions/eedi-mining-misconceptions-in-mathematics`

Math multiple-choice questions where each wrong-answer **distractor** is tagged
with the **expert-labeled misconception** behind it. This is the spine of the
project: it gives gold misconception labels (so diagnosis is measurable against
expert annotations) and ships a `misconception_mapping.csv` (MisconceptionId →
name) that **is your ready-made taxonomy** for the retrieval step and the
simulated learner.

Rough structure (confirm against the actual files): per question you get the
construct/subject/topic, question text, the correct answer, the answer texts for
each option, and the misconception ID for each wrong option.

Important realism note: in the original competition, a large share (~60%) of the
misconceptions in the test set were **unseen** during training. Mirror this — your
held-out split should include misconceptions the agent never saw — so your number
reflects real generalization, not memorization.

### Optional stretch: ASAP-SAS (Kaggle)

`kaggle.com/c/asap-sas`

~16k short-answer free-responses across 10 prompts (science/biology/English),
scored 0–3, QWK as the standard agreement metric. **Not math, no misconception
labels.** Use only if Day 6 has slack, to show the grader generalizes to
free-response (a QWK number on a second domain). Do not let it split the demo
narrative — the story is misconception diagnosis on math.

### Access (both)

Need a Kaggle account and to accept each competition's rules on its Rules tab
before downloading:

```bash
kaggle competitions download -c eedi-mining-misconceptions-in-mathematics
# optional stretch:
kaggle competitions download -c asap-sas
```

Licenses are **competition-specific** and some restrict use to the competition or
non-commercial purposes. For a non-commercial hackathon prototype this is normal
use, but read each Rules/Data tab yourself and don't describe the project as a
commercial product built on the data. (Not legal advice.)

Fallback if access is blocked: hand-build a small labeled set for one math topic
(30–60 items, a handful of misconceptions) — enough to demonstrate the method.

## Metrics (exact definitions)

1. **Misconception diagnosis accuracy — PRIMARY.** Given a wrong answer, does the
   agent's predicted misconception match the Eedi gold `MisconceptionId`?
   - Report **top-1 accuracy** and **MAP@k** (k≈25, Eedi's own metric) so it's
     comparable to the competition framing.
2. **% auto-taggable.** Share of wrong answers where confidence ≥ threshold AND,
   on those, diagnosis accuracy ≥ an expert-agreement bar. Tune the threshold to
   hold the accuracy bar.
3. **Teacher tagging time saved — HEADLINE.** Derived from % auto-taggable:
   "at X% auto-tagged at expert-level agreement, ~X% of misconception-tagging
   effort is returned to the teacher." State assumptions explicitly. This is the
   number the demo opens with. (Eedi's own purpose was making misconception
   tagging faster and more consistent — this framing is exactly on-narrative.)
4. **Remediation efficacy.** On the simulated learner: resolution rate of a
   *targeted* intervention vs. *generic* feedback, starting from the same known
   misconception. The learning-outcome evidence, with no real students.
5. **(Optional stretch) Grading agreement — QWK** on ASAP-SAS free-response:
   `sklearn.metrics.cohen_kappa_score(human, model, weights="quadratic")`.

## Simulated learner

Instantiate a model "student" with a **known, fixed misconception** taken from the
Eedi taxonomy. Give it the agent's intervention, then a follow-up item; run two
arms — targeted vs. generic feedback — and measure how often each resolves the
misconception over up to N attempts. Everything else held constant. Because the
starting misconception is ground truth, "did we resolve it" is well-defined, which
is what makes the learning-outcome claim defensible.

## Integrity rules (non-negotiable)

- **Held-out split with unseen misconceptions.** Reserve a test set the
  agent/prompts never see during iteration, and ensure it contains misconceptions
  held out entirely (mirroring Eedi). Tune on dev, report on held-out. State the
  split in the writeup.
- **No teaching to the test.** Never tweak prompts to pass specific eval examples.
  That inflates the number and is the fastest way to lose credibility.
- **Sanity-check the harness.** Hand-label ~10 items and confirm the harness
  agrees with you, so you trust the pipeline before trusting its numbers.
- **Report honestly.** Show where it fails (e.g. ambiguous or unseen
  misconceptions). A known failure mode reads as rigor; a too-clean number reads
  as fake.
- **Reproducible.** Every headline number must come out of `pytest` / the harness
  on command, with a fixed seed where randomness is involved.

## How to run

- `pytest eval/test_eval.py` — runs the harness, asserts threshold gates, prints
  the metrics table. Thresholds act as regression tests: a change that drops a
  metric fails the run.
- Keep the eval set ~150–300 examples. Cache results (see `state.py`) so repeated
  runs read from disk and conserve the Agent SDK credit.
