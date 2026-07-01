"""Misconception-diagnosis metrics: top-1 accuracy and MAP@k (Eedi's own metric).

Definitions (see EVAL.md):
- top-1 accuracy: fraction of instances whose predicted best-fit misconception id
  equals the gold MisconceptionId.
- MAP@k: mean average precision at k over the ranked misconception ids. Each
  instance has exactly one relevant (gold) id, so AP@k reduces to
  1/rank if the gold id appears within the first k, else 0. k=25 mirrors Eedi.
"""
from __future__ import annotations


def recall_at_k(candidate_id_lists: list[list[str]], gold: list[str]) -> float:
    """Retrieval ceiling: fraction of items whose gold misconception survives into
    the retrieved candidate list. If the gold isn't retrieved, the diagnoser can
    never pick it — so this bounds top-1/MAP from above.
    """
    if not gold:
        return 0.0
    hits = sum(1 for cands, g in zip(candidate_id_lists, gold, strict=True) if g in cands)
    return hits / len(gold)


def qwk(human: list[int], model: list[int]) -> float:
    """Quadratic-weighted Cohen's kappa — the ASAP-SAS free-response agreement
    metric (EVAL.md, optional stretch). Not used on the Eedi MCQ spine; provided
    so the free-response grader has its metric ready when/if that stretch runs.
    """
    from sklearn.metrics import cohen_kappa_score

    return float(cohen_kappa_score(human, model, weights="quadratic"))


def top1_accuracy(preds: list[str | None], gold: list[str]) -> float:
    if not gold:
        return 0.0
    correct = sum(1 for p, g in zip(preds, gold, strict=True) if p is not None and p == g)
    return correct / len(gold)


def average_precision_at_k(ranked: list[str], gold_id: str, k: int = 25) -> float:
    """AP@k for a single relevant item = 1/rank if gold within top-k else 0."""
    for i, mid in enumerate(ranked[:k], start=1):
        if mid == gold_id:
            return 1.0 / i
    return 0.0


def map_at_k(ranked_lists: list[list[str]], gold: list[str], k: int = 25) -> float:
    if not gold:
        return 0.0
    total = sum(
        average_precision_at_k(r, g, k) for r, g in zip(ranked_lists, gold, strict=True)
    )
    return total / len(gold)


def summarize(
    preds: list[str | None],
    ranked_lists: list[list[str]],
    gold: list[str],
    k: int = 25,
) -> dict[str, float]:
    return {
        "n": float(len(gold)),
        "top1_accuracy": top1_accuracy(preds, gold),
        f"map@{k}": map_at_k(ranked_lists, gold, k),
    }


def format_table(metrics: dict[str, float], split_name: str = "") -> str:
    header = f"=== Diagnosis metrics{f' [{split_name}]' if split_name else ''} ==="
    lines = [header]
    for key, val in metrics.items():
        lines.append(f"  {key:<16} {val:.4f}" if key != "n" else f"  {key:<16} {int(val)}")
    return "\n".join(lines)
