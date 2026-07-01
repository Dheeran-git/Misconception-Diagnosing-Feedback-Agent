# data/ — datasets + cache (gitignored)

Everything in this directory except this README is gitignored (datasets are
licensed; the cache is derived). Put the real files here and the harness uses them
automatically.

## Expected files

**Eedi — Mining Misconceptions in Mathematics** (spine; required for headline numbers)
- `data/train.csv` — questions, 4 answer texts, and per-distractor
  `Misconception{A..D}Id`.
- `data/misconception_mapping.csv` — `MisconceptionId,MisconceptionName` (the taxonomy).
- Source: `kaggle.com/competitions/eedi-mining-misconceptions-in-mathematics` →
  Data tab (accept the rules first). `eval/dataset.py` auto-prefers these over the
  synthetic fixture in `eval/fixtures/`.

**ASAP-SAS** (optional free-response stretch — QWK)
- `data/asap/train.tsv` — Kaggle ships `train_rel_2.tsv`; rename to `train.tsv`
  (columns `Id, EssaySet, Score1, Score2, EssayText`).
- `data/asap/meta.json` — per-`EssaySet` `{question, rubric, max_score}` (rubrics
  ship as separate description docs; a parsed version may already be here).
- Source: `kaggle.com/c/asap-sas` → Data tab.

## Runtime files (auto-created, gitignored)
- `data/cache.sqlite` — diagnosis/grade cache, attempts, triage queue.

## Reproduce the real numbers
```bash
uv run python -m eval.benchmark --n 50 --k 1     # diagnosis top-1 / MAP@25 / recall@25
uv run python -m eval.benchmark --n 25 --k 3     # + confidence, % auto-taggable, time-saved
```
Cached + resumable: re-running the same config only pays for new items.
