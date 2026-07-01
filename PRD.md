# PRD — Misconception-Diagnosing Feedback Agent

**Event:** EdTech 3.0 · **Track 2:** Assessment & Feedback Automation
**Builder:** solo · **Window:** June 18–25, 2026

## 1. Problem

Teachers lose a large share of their time to grading and feedback. Existing
auto-graders mostly output a score and "correct/incorrect" — they don't explain
*why* a student went wrong, and they don't do anything about it. So the work that
actually helps a learner (diagnosing the misconception and addressing it) still
falls on the teacher, or doesn't happen. Tagging *which* misconception a wrong
answer reveals is slow, inconsistent, and hard to scale.

## 2. What we're building

An autonomous feedback agent for **multiple-choice math** items that:

1. Assesses the student's chosen answer (correct vs. which distractor).
2. Diagnoses the *specific* misconception behind the wrong choice — matched
   against expert gold labels — not just "incorrect".
3. Acts: produces a targeted Socratic intervention aimed at that misconception —
   a counterexample or a single probing question, never the answer outright.
4. Verifies on a follow-up attempt whether the misconception is resolved, and
   escalates the intervention autonomously if it isn't.
5. Emits a calibrated confidence and routes low-confidence diagnoses to a
   teacher tagging-review queue, so teacher attention goes where it's needed.

**One-line pitch:** Most graders tell a student they're wrong. This one figures
out *why* — names the exact misconception — does something about it, and checks
whether it worked.

**Spine dataset:** Eedi — Mining Misconceptions in Mathematics (math MCQs with
expert-labeled misconceptions per distractor). See `EVAL.md`.

## 3. Users

- **Teacher** — reviews the tagging-triage queue, sees confidence flags and the
  agent's evidence, overrides when needed. Wants time back and trustworthy,
  consistent misconception tagging.
- **Student** — receives targeted, non-spoiler feedback and a follow-up that
  helps them self-correct.

## 4. Why this track, this build

Solo + no live test users + ML/agents strength → Track 2 is the one track where
**measurable results require no real users**: Eedi's expert misconception labels
are the gold standard your agent is scored against. The build is engineered to be
strongest on the two heaviest scoring axes (Impact and Autonomy). See map below.

## 5. Judging criteria → product requirements

| Criterion (weight) | What it demands | How this build delivers |
|---|---|---|
| Educational Impact (30%) | Measurable learning outcome | Remediation-efficacy experiment (targeted vs. generic on a simulated learner) + teacher tagging-time-saved number |
| Agent Intelligence & Autonomy (30%) | Reasons and *acts*, multi-step, autonomous | Closed assess→diagnose→remediate→verify→escalate loop; SymPy tool use; autonomous escalation + triage routing |
| Scalability (20%) | Works beyond a toy | Batch diagnosis throughput + % auto-taggable at an expert-agreement bar; caching |
| UX for Learners & Teachers (20%) | Usable by both | Streamlit teacher tagging-triage view + student feedback view, legible at a glance |

## 6. Functional requirements

- **FR1 Assess.** Given an MCQ math item + the student's chosen answer →
  correctness + confidence, as a validated Pydantic object.
- **FR2 Diagnose.** For wrong answers → a specific misconception drawn from the
  Eedi taxonomy (with retrieval), plus evidence; matched against gold for eval.
- **FR3 Remediate.** Generate a targeted Socratic intervention for that
  misconception. Must not reveal the final answer.
- **FR4 Verify + escalate.** On a follow-up attempt (simulated learner or next
  item), decide resolved / not-resolved; if not resolved, escalate (stronger hint
  / different representation) — the agent makes this call and logs its reasoning.
- **FR5 Confidence + triage.** Self-consistency over multiple samples → confidence;
  below threshold → teacher tagging-review queue.
- **FR6 Math tool.** Agent calls SymPy to check algebraic/numeric equivalence
  rather than trusting LLM arithmetic.
- **FR7 Persistence.** Attempts, triage queue, and diagnosis cache in SQLite.
- **FR8 Dashboards.** Teacher tagging-triage + metrics view; student feedback view.
- **FR9 Trace logging.** Every step and tool call logged for debugging + demo.
- **FR10 (optional stretch).** Rubric-aware free-response grader + QWK on ASAP-SAS,
  to show generalization beyond MCQ. Only if Day 6 has slack.

## 7. Non-goals (explicitly out of scope this week)

- Multi-subject support (math only).
- Auth / multi-tenant / accounts / hosting at scale.
- A custom React/Next frontend.
- Fine-tuning a model.
- Mobile apps, LMS integrations, real student data / PII.
- Anything requiring live classroom users (that's Track 4, not us).

## 8. Success metrics (defined precisely in EVAL.md)

- **Misconception diagnosis accuracy (PRIMARY):** top-1 accuracy + MAP@k vs. Eedi
  gold labels.
- **% auto-taggable:** share diagnosable at/above an expert-agreement threshold.
- **Teacher tagging time saved (HEADLINE):** derived from % auto-taggable; the
  number the demo opens with.
- **Remediation efficacy:** resolution rate of targeted vs. generic feedback on
  the simulated learner.
- **(Optional) QWK** on ASAP-SAS free-response.

## 9. Demo requirements (this is scored too — reserve Day 7)

- 2–3 min video. **Open with the single headline number in the first 10s.**
- Show the loop running live on one example: wrong MCQ answer → named misconception
  (with evidence) → Socratic hint → follow-up attempt → verify/escalate.
- Show the teacher tagging-triage queue with confidence flags.
- One scripted "active diagnosis" moment (agent picks the next problem to
  disambiguate between two misconceptions) — optional flourish, cut if flaky.
- Writeup leads with metrics; README states how every number is computed,
  including the held-out split and the unseen-misconception handling.
- Include AI-use disclosure if the rules require it (verify hackathon rules).
