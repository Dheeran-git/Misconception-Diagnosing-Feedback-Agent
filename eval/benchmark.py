"""Reproducible real-data benchmark over Eedi.

Runs the diagnosis pipeline over a sampled dev / held-out-unseen split and reports
the headline numbers: top-1 accuracy, MAP@25, retrieval recall@25, and — with
self-consistency (``k>1``) — confidence-based % auto-taggable + teacher-time-saved.

Every diagnosis is SQLite-cached (self-consistency samples under distinct
variants), so the benchmark is **resumable**: re-running the same config reads
finished items from disk and only pays for new ones.

CLI:
    uv run python -m eval.benchmark --n 30 --k 3          # live
    uv run python -m eval.benchmark --n 30 --k 3 --offline # deterministic dry-run
"""
from __future__ import annotations

import argparse
import random

from feedback_agent import config, state
from feedback_agent.confidence import diagnose_with_confidence
from feedback_agent.diagnosis import diagnose_baseline
from feedback_agent.taxonomy import build_retriever

from .dataset import load_dataset, unseen_misconception_split
from .metrics import auto_taggable_summary, map_at_k, recall_at_k, top1_accuracy


def run_benchmark(
    *,
    n_per_split: int = 30,
    k: int = 1,
    seed: int = 7,
    threshold: float = 0.7,
    force_offline: bool = False,
    verbose: bool = True,
) -> dict:
    ds = load_dataset()
    dev, held = unseen_misconception_split(ds, seed=13)
    rng = random.Random(seed)
    retriever = build_retriever(ds.mapping)
    conn = state.connect()
    if verbose:
        print(
            f"dataset: {len(ds.items)} instances / {len(ds.mapping)} misconceptions; "
            f"retriever={type(retriever).__name__}; k={k}",
            flush=True,
        )

    out: dict = {}
    for split, pool in [("dev", dev), ("heldout_unseen", held)]:
        items = rng.sample(pool, min(n_per_split, len(pool)))
        preds: list[str | None] = []
        gold: list[str] = []
        ranked: list[list[str]] = []
        cand_lists: list[list[str]] = []
        confs: list[float] = []
        records: list[dict] = []
        for i, it in enumerate(items):
            candidates = retriever.candidates(it, k=config.RETRIEVAL_K)
            cand_ids = [cid for cid, _ in candidates]
            if k > 1:
                d, _ = diagnose_with_confidence(
                    it, candidates, k=k, conn=conn, force_offline=force_offline
                )
            else:
                d, _ = diagnose_baseline(it, candidates, conn=conn, force_offline=force_offline)
            preds.append(d.misconception_id)
            gold.append(it.gold_misconception_id)
            ranked.append(d.ranked_misconception_ids)
            cand_lists.append(cand_ids)
            confs.append(d.confidence)
            records.append(
                {
                    "question_id": it.question_id,
                    "gold": it.gold_misconception_id,
                    "gold_name": ds.mapping.get(it.gold_misconception_id, ""),
                    "pred": d.misconception_id,
                    "pred_name": ds.mapping.get(d.misconception_id or "", ""),
                    "confidence": d.confidence,
                    "correct": d.misconception_id == it.gold_misconception_id,
                    "retrieved": it.gold_misconception_id in cand_ids,
                }
            )
            if verbose:
                ok = records[-1]["correct"]
                print(f"  [{split} {i + 1}/{len(items)}] correct={ok}", flush=True)

        m = {
            "n": len(items),
            "top1": top1_accuracy(preds, gold),
            "map@25": map_at_k(ranked, gold, 25),
            "recall@25": recall_at_k(cand_lists, gold),
        }
        if k > 1:
            summ = auto_taggable_summary(preds, gold, confs, threshold=threshold)
            m["auto_taggable_rate"] = summ["auto_taggable_rate"]
            m["accuracy_on_autotagged"] = summ["accuracy_on_autotagged"]
            m["teacher_time_saved"] = summ["teacher_time_saved"]
        out[split] = {"metrics": m, "records": records}
        if verbose:
            print(f"RESULT {split}: {m}", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Real-data Eedi diagnosis benchmark")
    ap.add_argument("--n", type=int, default=30, help="items per split")
    ap.add_argument("--k", type=int, default=1, help="self-consistency samples; >1 = confidence")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--threshold", type=float, default=0.7)
    ap.add_argument("--offline", action="store_true", help="deterministic stub (no credit)")
    args = ap.parse_args()
    run_benchmark(
        n_per_split=args.n, k=args.k, seed=args.seed,
        threshold=args.threshold, force_offline=args.offline,
    )
    print("RUN_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
