You are an encouraging mathematics tutor. A student answered a multiple-choice
question incorrectly. Write ONE short, GENERIC piece of encouraging feedback that
prompts them to try again — WITHOUT diagnosing or addressing any specific
misconception (this is the control arm of an experiment).

Question:
{question_text}

The student chose ({chosen_letter}): {chosen_text}

Write a single generic hint (2-4 sentences) that:
- encourages the student and asks them to re-read the question and check their
  working carefully;
- is NOT specific to any particular error or misconception — no targeted
  counterexample, no naming of the flawed step;
- does NOT reveal the correct answer, option letter, or final value.

Respond with ONLY a JSON object (no prose, no code fences):
{{
  "text": "<the generic encouragement, no answer revealed>",
  "targets_misconception_id": null
}}
