# eval/fixtures — SYNTHETIC data, not Eedi

These CSVs are a **tiny hand-written stand-in** on the *exact Eedi
"Mining Misconceptions in Mathematics" schema*, so the harness and `pytest` run
before the real Kaggle data is available. They are **not** Eedi data and any
number produced on them is a **pipeline smoke test, not a reported metric**.

- `misconception_mapping.csv` — 6 invented linear-equation misconceptions
  (`MisconceptionId`, `MisconceptionName`), same columns as Eedi's mapping.
- `eedi_train_sample.csv` — 8 invented questions with labeled wrong-answer
  distractors, same columns as Eedi's `train.csv`
  (`QuestionId`, `CorrectAnswer`, `QuestionText`, `Answer{A..D}Text`,
  `Misconception{A..D}Id`, …). Blank misconception cells = unlabeled distractors.

## Swapping in real Eedi

Drop the real `train.csv` and `misconception_mapping.csv` into `data/`
(gitignored). `eval/dataset.py` prefers `data/` and only falls back to this
fixture — no code change needed.
