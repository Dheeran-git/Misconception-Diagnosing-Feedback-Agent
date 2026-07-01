"""Day-1 eval gate.

Runs the baseline diagnoser over the dataset (synthetic fixture until real Eedi
data is dropped into data/) and asserts the pipeline produces *valid* metrics.
These are **loose regression gates**, not quality thresholds — the point of Day 1
is that measuring works, and that re-runs hit the cache instead of the model.

Runs in OFFLINE mode by default so the suite is deterministic and spends no
Agent SDK credit. When the live SDK path is exercised elsewhere it populates the
same cache, and these tests then read the real predictions from disk.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from feedback_agent import state
from feedback_agent.models import DiagnosisItem

from . import harness
from .dataset import load_dataset, unseen_misconception_split
from .metrics import average_precision_at_k, format_table, map_at_k, top1_accuracy


@pytest.fixture(scope="module")
def dataset():
    return load_dataset()


@pytest.fixture()
def db(tmp_path):
    # Isolated cache DB per test so we never touch data/cache.sqlite.
    conn = state.connect(tmp_path / "test_cache.sqlite")
    yield conn
    conn.close()


def test_dataset_loads_and_explodes(dataset):
    assert len(dataset.items) >= 8, "expected several gradable distractor instances"
    assert dataset.mapping, "misconception mapping should be non-empty"
    # every gradable item must carry a gold id that exists in the taxonomy
    for it in dataset.items:
        assert it.gold_misconception_id in dataset.mapping
        assert it.chosen_answer != it.correct_answer


def test_unseen_split_holds_misconceptions_out_entirely(dataset):
    dev, heldout = unseen_misconception_split(dataset, seed=13)
    assert dev and heldout, "both splits should be non-empty"
    dev_ids = {it.gold_misconception_id for it in dev}
    held_ids = {it.gold_misconception_id for it in heldout}
    # the whole point: held-out misconceptions never appear in dev
    assert dev_ids.isdisjoint(held_ids)


def test_metric_math():
    # AP@k for a single relevant item is 1/rank.
    assert average_precision_at_k(["a", "b", "c"], "b", k=25) == pytest.approx(0.5)
    assert average_precision_at_k(["a", "b", "c"], "z", k=25) == 0.0
    assert top1_accuracy(["a", "b", None], ["a", "x", "y"]) == pytest.approx(1 / 3)
    assert map_at_k([["a", "b"], ["b", "a"]], ["a", "a"], k=25) == pytest.approx(0.75)


def test_baseline_runs_and_reports(dataset, db, capsys):
    dev, heldout = unseen_misconception_split(dataset, seed=13)
    result = harness.run(dev, dataset.mapping, conn=db, force_offline=True, split_name="dev")

    m = result.metrics
    assert m["n"] == len(dev)
    assert 0.0 <= m["top1_accuracy"] <= 1.0
    assert 0.0 <= m["map@25"] <= 1.0
    # offline baseline should do strictly better than nothing on MAP (ranking works)
    assert m["map@25"] > 0.0

    print("\n" + format_table(m, "dev (offline stub)"))
    print("modes:", dict(result.modes))


def test_rerun_hits_cache(dataset, db):
    items = dataset.items[:5]
    first = harness.run(items, dataset.mapping, conn=db, force_offline=True)
    assert first.modes["offline"] == len(items)
    # second pass over the same items + same DB must be served entirely from cache
    second = harness.run(items, dataset.mapping, conn=db, force_offline=True)
    assert second.modes["cache"] == len(items)
    assert second.modes["offline"] == 0


def test_fixture_files_present():
    root = Path(__file__).resolve().parent / "fixtures"
    assert (root / "eedi_train_sample.csv").exists()
    assert (root / "misconception_mapping.csv").exists()


def test_assess_correctness_deterministic():
    from feedback_agent.grading import assess

    right = assess("q1", "B", "B", chosen_answer_text="x = 4", correct_answer_text="x = 4")
    assert right.is_correct is True
    assert right.confidence == 1.0

    wrong = assess("q1", "a", "B")  # case-insensitive, still wrong
    assert wrong.is_correct is False
    assert wrong.chosen_answer == "A" and wrong.correct_answer == "B"


def test_assess_cached_hits_cache_and_logs(db):
    from feedback_agent.grading import assess_cached
    from feedback_agent.state import get_attempts

    first, mode1 = assess_cached(db, "q42", "C", "A", chosen_answer_text="x = 8")
    assert mode1 == "computed" and first.is_correct is False
    second, mode2 = assess_cached(db, "q42", "C", "A")
    assert mode2 == "cache"
    assert second.model_dump() == first.model_dump()

    # the miss logged exactly one 'assess' attempt (the cache hit does not re-log)
    attempts = get_attempts(db, "q42")
    assert len(attempts) == 1 and attempts[0]["step"] == "assess"


def test_assess_choice_uses_item_correct_answer(dataset):
    from feedback_agent.grading import assess_choice

    item = dataset.items[0]  # a wrong-distractor instance
    # picking the item's correct option is correct; picking the distractor is not
    assert assess_choice(item, item.correct_answer).is_correct is True
    assert assess_choice(item, item.chosen_answer).is_correct is False


def test_recall_at_k_metric():
    from .metrics import recall_at_k

    cands = [["a", "b", "c"], ["x", "y"]]
    assert recall_at_k(cands, ["b", "z"]) == pytest.approx(0.5)
    assert recall_at_k(cands, ["a", "x"]) == pytest.approx(1.0)


def test_incontext_retriever_is_blind_and_capped(dataset):
    from feedback_agent.taxonomy import InContextRetriever, build_retriever

    item = dataset.items[0]
    r = build_retriever(dataset.mapping)  # small taxonomy -> in-context
    assert isinstance(r, InContextRetriever)
    all_c = r.candidates(item)
    assert len(all_c) == len(dataset.mapping)
    # capping must NOT special-case the gold (blind retrieval)
    capped_ids = [cid for cid, _ in r.candidates(item, k=2)]
    assert len(capped_ids) == 2
    assert capped_ids == list(dataset.mapping.keys())[:2]


def test_build_retriever_selects_by_size(dataset):
    from feedback_agent.taxonomy import InContextRetriever, build_retriever

    assert isinstance(build_retriever(dataset.mapping, kind="incontext"), InContextRetriever)
    # 'auto' on the tiny fixture stays in-context (no model download in tests)
    assert isinstance(build_retriever(dataset.mapping, kind="auto"), InContextRetriever)


def test_harness_reports_recall(dataset, db):
    dev, _ = unseen_misconception_split(dataset, seed=13)
    r = harness.run(dev, dataset.mapping, conn=db, force_offline=True)
    # in-context retriever returns the whole (small) taxonomy -> gold always present
    key = next(k for k in r.metrics if k.startswith("recall@"))
    assert r.metrics[key] == pytest.approx(1.0)


@pytest.mark.skipif(
    os.getenv("FEEDBACK_AGENT_RUN_EMBED") != "1",
    reason="embedding retriever downloads a model + needs network; set FEEDBACK_AGENT_RUN_EMBED=1",
)
def test_embedding_retriever_narrows_large_taxonomy(dataset):
    from feedback_agent.taxonomy import EmbeddingRetriever

    # 6 real linear-equation misconceptions + noise on unrelated topics
    mapping = dict(dataset.mapping)
    noise = {
        f"n{i}": name
        for i, name in enumerate(
            [
                "Confuses the area and perimeter of a rectangle",
                "Believes the mean is the middle value of a sorted list",
                "Thinks probability can exceed 1",
                "Rounds to the nearest ten instead of the nearest whole number",
                "Confuses acute and obtuse angles",
                "Believes multiplying two negatives gives a negative",
                "Thinks a fraction is larger when its denominator is larger",
                "Confuses radius and diameter of a circle",
            ],
            start=1,
        )
    }
    mapping.update(noise)

    r = EmbeddingRetriever(mapping)
    item = next(it for it in dataset.items if it.gold_misconception_id in dataset.mapping)
    top = [cid for cid, _ in r.candidates(item, k=6)]
    assert len(top) == 6
    assert item.gold_misconception_id in top  # gold survives retrieval
    # at least one obviously-unrelated noise id is filtered out
    assert any(cid not in top for cid in noise)


def test_qwk_metric():
    from .metrics import qwk

    assert qwk([0, 1, 2, 3], [0, 1, 2, 3]) == pytest.approx(1.0)
    # closer-but-wrong scores beat far-off ones under quadratic weighting
    near = qwk([0, 1, 2, 3], [1, 1, 2, 2])
    far = qwk([0, 1, 2, 3], [3, 2, 1, 0])
    assert near > far


def test_diagnosis_item_shape():
    it = DiagnosisItem(
        question_id="q_A",
        question_text="Solve 2x=4",
        correct_answer="B",
        correct_answer_text="x=2",
        chosen_answer="A",
        chosen_answer_text="x=8",
        gold_misconception_id="1",
    )
    assert it.chosen_answer == "A"
