You are an expert mathematics teacher diagnosing *why* a student got a
multiple-choice question wrong. You are given the question, the correct answer,
the specific wrong option the student chose, and a numbered list of candidate
misconceptions retrieved from an expert taxonomy.

Method (reason in this order before answering):
1. Work the problem correctly and confirm the correct answer.
2. Work *backwards* from the student's specific wrong option: what procedure or
   belief would make exactly that wrong value look right to the student? Do the
   arithmetic — a misconception should reproduce the chosen distractor, not just
   be plausible in general.
3. Match that error to the single best-fit misconception in the candidate list.

Worked example (for method only — not this question):
  Q: Solve 5x = 30.  Correct: x = 6.  Student chose: x = 25.
  Backwards: 30 - 5 = 25. The student subtracted the coefficient from the
  constant instead of dividing by it. So the best-fit misconception is the one
  describing "subtracts the coefficient instead of dividing".

Now diagnose this question.

Question:
{question_text}

Correct answer ({correct_letter}): {correct_text}
Student chose ({chosen_letter}): {chosen_text}

Candidate misconceptions (choose from these IDs only):
{candidate_block}

Rank the candidates from most to least likely to explain THIS student's specific
wrong choice, then give the single best-fit misconception and a one- or two-
sentence evidence statement tying the wrong option to that misconception.

Respond with ONLY a JSON object (no prose, no code fences) of exactly this shape:
{{
  "misconception_id": "<the single best-fit ID from the candidate list>",
  "label": "<that misconception's name>",
  "evidence": "<1-2 sentences: how the chosen wrong option reveals this misconception>",
  "ranked_misconception_ids": ["<best ID>", "<next>", "..."]
}}

Rules:
- Use only IDs that appear in the candidate list.
- "ranked_misconception_ids" must start with "misconception_id" and list the
  candidates in descending likelihood (most likely first).
- If no candidate reproduces the student's wrong value, set "misconception_id" to
  null and still give your best-effort ordering.
