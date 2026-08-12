# Evaluation

The gold set is what separates this from an assembled demo. Do not skip it and
do not let a model produce it.

## Building the gold set

```bash
python -m eval.sample --n 25 --out eval/worksheet.csv
```

Samples stratified across at least 4 benches and 4 outcomes, and dumps each
order's page text alongside the worksheet so labelling does not require opening
PDFs.

A human fills in the expected value for every field. 6–10 hours. There is no
way around this and no substitute for it.

```bash
python -m eval.import --file eval/worksheet.csv
```

## Metrics reported

Per field name:

- **Precision** — of the fields we claimed, how many were right
- **Recall** — of the fields actually present in the document, how many we found
- **Exact match** for text fields
- **Within 1%** for numeric fields, alongside exact match
- **Verification rejection rate** — fields the span verifier threw out

Precision and recall are different failure modes and both go in the README.
A tool that finds 40% of fields but is right about all of them is useful. A
tool that finds 95% and is wrong about a fifth of them is dangerous.

```bash
python -m eval.report          # table to stdout, JSON to eval/latest.json
```

## Rules

- `backend/eval/gold_labels/` is human ground truth. Never regenerate it,
  never let an agent write to it.
- Re-run the report after every prompt or model change. Record the delta.
- If accuracy drops, revert first and investigate second.
- The README quotes real numbers from `eval/latest.json`, including the ones
  that look bad.
