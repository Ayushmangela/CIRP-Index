---
name: run-eval
description: Run and interpret the gold-set accuracy report. Use after any change to the extraction prompt, model, parsing logic or verifier, before updating the README's accuracy numbers, or when asked how well extraction is performing.
---

# Running the evaluation

Read docs/EVALUATION.md for the metric definitions.

```bash
python -m eval.report
```

Outputs a per-field table to stdout and JSON to `eval/latest.json`.

## Interpreting it

Report precision and recall separately, always. They fail differently:

- Low precision, high recall — the model is confident and wrong. Serious.
  Tighten the prompt or the verifier.
- High precision, low recall — the model is cautious, or documents phrase things
  in ways the prompt does not anticipate. Acceptable, and honest to state.
- High rejection rate — the model is paraphrasing instead of quoting. Fix the
  prompt's quoting instruction, never the verifier's strictness.

## Rules

- `backend/eval/gold_labels/` is human ground truth. Never write to it, never
  regenerate it, never "correct" a label because the model disagrees.
- Record before and after numbers for every change. State the delta plainly.
- If accuracy drops, revert first, investigate second.
- Never tune against the gold set until the numbers look good. That is fitting
  to the test set and it makes the reported accuracy meaningless.

## Reporting to the human

Give the table, the delta from last run, and one sentence on what changed and
why. Do not editorialise the numbers upward. If something got worse, lead with
that.
