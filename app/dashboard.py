"""Streamlit dashboard — teacher triage view + student feedback view.

Thin and legible by design (PLAN.md Day 6). Both views import the SAME agent
modules the eval harness uses — there is no HTTP layer between the UI and the
agent. Run with:

    uv run streamlit run app/dashboard.py

Toggle "offline (fast)" in the sidebar to demo without spending Agent SDK credit
(deterministic stub); untoggle to run the real model.

The data-shaping helpers below are pure (no Streamlit) so they can be unit-tested;
Streamlit rendering happens only under ``if __name__ == "__main__"``.
"""
from __future__ import annotations

import sys
from pathlib import Path

# Make the src/ package importable whether launched via uv (installed) or directly.
_SRC = Path(__file__).resolve().parents[1] / "src"
if _SRC.exists() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from feedback_agent import state  # noqa: E402
from feedback_agent.diagnosis import diagnose_baseline  # noqa: E402
from feedback_agent.grading import assess  # noqa: E402
from feedback_agent.models import DiagnosisItem  # noqa: E402
from feedback_agent.remediation import generate_intervention, leaks_answer  # noqa: E402
from feedback_agent.taxonomy import build_retriever  # noqa: E402


# --------------------------------------------------------------------------- #
# Pure helpers (testable — no Streamlit)
# --------------------------------------------------------------------------- #
def load_data():
    """Load the active dataset (real Eedi in data/ if present, else fixture)."""
    from eval.dataset import load_dataset  # local import: eval depends on feedback_agent

    return load_dataset()


def student_feedback(
    item: DiagnosisItem, mapping: dict[str, str], *, conn, force_offline: bool = True
) -> dict:
    """Run assess → diagnose → remediate for one chosen answer and return the
    student-facing result (no answer leak)."""
    a = assess(
        item.question_id, item.chosen_answer, item.correct_answer,
        chosen_answer_text=item.chosen_answer_text, correct_answer_text=item.correct_answer_text,
    )
    if a.is_correct:
        return {"is_correct": True, "diagnosis": None, "intervention": None}

    candidates = build_retriever(mapping).candidates(item)
    diagnosis, _ = diagnose_baseline(item, candidates, conn=conn, force_offline=force_offline)
    intervention, _ = generate_intervention(
        item, diagnosis, targeted=True, force_offline=force_offline
    )
    return {
        "is_correct": False,
        "diagnosis": diagnosis,
        "intervention": intervention,
        "leaked": leaks_answer(intervention.text, item.correct_answer_text),
    }


def triage_rows(conn) -> list[dict]:
    """Teacher queue: unresolved low-confidence diagnoses, most-uncertain first."""
    return state.triage_items(conn, only_unresolved=True)


# --------------------------------------------------------------------------- #
# Streamlit rendering
# --------------------------------------------------------------------------- #
def _render():
    import streamlit as st

    st.set_page_config(page_title="Misconception Feedback Agent", layout="wide")
    st.title("🧮 Misconception-Diagnosing Feedback Agent")

    with st.sidebar:
        view = st.radio("View", ["Student feedback", "Teacher triage"])
        force_offline = st.toggle("offline (fast, no credit)", value=True)
        st.caption("Untoggle to run the real Claude Agent SDK (slower).")

    data = load_data()
    conn = state.connect()

    if view == "Student feedback":
        _render_student(st, data, conn, force_offline)
    else:
        _render_teacher(st, data, conn)


def _render_student(st, data, conn, force_offline):
    st.header("Student feedback")
    labels = [
        f"{it.question_id} · {it.question_text}  (you chose: {it.chosen_answer_text})"
        for it in data.items
    ]
    idx = st.selectbox(
        "Pick a question + answer", range(len(labels)), format_func=lambda i: labels[i]
    )
    item = data.items[idx]

    if st.button("Get feedback", type="primary"):
        with st.spinner("Diagnosing…"):
            res = student_feedback(item, data.mapping, conn=conn, force_offline=force_offline)
        if res["is_correct"]:
            st.success("Correct! ✅")
            return
        dg = res["diagnosis"]
        st.error(f"Not quite — you chose **{item.chosen_answer_text}**.")
        st.subheader("What went wrong (misconception)")
        st.markdown(f"**{data.mapping.get(dg.misconception_id, dg.label or '—')}**")
        if dg.evidence:
            st.caption(dg.evidence)
        st.subheader("A hint to try again")
        st.info(res["intervention"].text)
        if res["leaked"]:
            st.warning("⚠️ guardrail: this hint may reveal the answer (would be regenerated live).")


def _render_teacher(st, data, conn):
    st.header("Teacher tagging-triage queue")
    rows = triage_rows(conn)
    st.metric("Items awaiting review", len(rows))
    if not rows:
        st.info("Queue is empty. Run the batch tagging pipeline to populate it.")
        return
    for r in rows:
        dg = r["diagnosis"] or {}
        conf = r["confidence"] or 0.0
        flag = "🔴" if conf < 0.7 else "🟢"
        with st.expander(f"{flag} {r['question_id']} · confidence {conf:.2f}"):
            label = dg.get("label") or dg.get("misconception_id")
            st.markdown(f"**Predicted misconception:** {label}")
            if dg.get("evidence"):
                st.caption(dg["evidence"])
            st.caption(f"queued {r['created_at']}")


if __name__ == "__main__":
    _render()
