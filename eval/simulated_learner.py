"""Simulated learner: an LLM 'student' instantiated with a known misconception.

Used for the remediation-efficacy experiment (EVAL.md): give the student a
follow-up attempt with vs. without a targeted intervention and measure how often
the misconception resolves. Because the starting misconception is ground truth,
"did we resolve it" is well-defined.

- Offline stub (deterministic, for pytest): the student applies its misconception
  and answers wrong, UNLESS given an intervention that targets exactly that
  misconception, in which case it self-corrects. This is a *mechanism* — it makes
  the loop/escalation/experiment testable without credit; it is NOT the reported
  efficacy number (that circularity is why the real number comes from the live
  student, which may or may not be swayed by a hint).
- Live path: role-plays the student via the SDK and returns a free-form answer.
"""
from __future__ import annotations

from feedback_agent import config
from feedback_agent.models import DiagnosisItem, Intervention, LearnerAttempt
from feedback_agent.prompts import LEARNER_PROMPT_VERSION, load_prompt
from feedback_agent.sdk_client import live_json


class SimulatedLearner:
    def __init__(self, misconception_id: str, misconception_name: str, *, model: str | None = None):
        self.misconception_id = misconception_id
        self.misconception_name = misconception_name
        self.model = model or config.FAST_MODEL

    def _stub(self, item: DiagnosisItem, intervention: Intervention | None) -> LearnerAttempt:
        # Mechanism model: a *targeted* hint (one that names a specific
        # misconception) resolves the student; no hint or a generic one does not.
        # The finer coupling — a targeted hint only helps when the diagnosis is
        # actually correct — is left to the live learner, which reasons about the
        # hint's content rather than just its presence.
        targeted = intervention is not None and intervention.targets_misconception_id is not None
        if targeted:
            return LearnerAttempt(
                answer=item.correct_answer_text,
                reasoning="(stub) the targeted hint exposed my mistake",
            )
        return LearnerAttempt(
            answer=item.chosen_answer_text,
            reasoning="(stub) I applied my usual (mistaken) method",
        )

    def attempt(
        self,
        item: DiagnosisItem,
        intervention: Intervention | None = None,
        *,
        force_offline: bool = False,
    ) -> tuple[LearnerAttempt, str]:
        """Return (LearnerAttempt, mode). mode is 'live' or 'offline'."""
        if force_offline or config.OFFLINE:
            return self._stub(item, intervention), "offline"

        hint_block = (
            f'Your tutor offered this hint:\n"{intervention.text}"'
            if intervention is not None
            else "No tutor hint has been given yet."
        )
        prompt = load_prompt(LEARNER_PROMPT_VERSION).format(
            misconception_name=self.misconception_name,
            hint_block=hint_block,
            question_text=item.question_text,
        )
        try:
            data = live_json(
                prompt,
                LearnerAttempt.model_json_schema(),
                model=self.model,
                system_prompt="You are role-playing a specific student for an experiment.",
            )
            return (
                LearnerAttempt(
                    answer=str(data.get("answer", "")),
                    reasoning=str(data.get("reasoning", "")),
                ),
                "live",
            )
        except Exception:
            return self._stub(item, intervention), "offline"
