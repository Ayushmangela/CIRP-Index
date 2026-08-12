# 0001 — Evidence-first architecture

**Status:** accepted
**Date:** 2026-08-12

## Context

LLM extraction on legal and financial documents produces fluent, plausible,
occasionally wrong output. A wrong claim amount attributed to a real
liquidation order is worse than no tool, because it does not announce itself.

Self-reported model confidence scores are not calibrated. Displaying "94%
confidence" implies a measurement that was never made.

## Decision

Every displayed fact is backed by a verbatim quote that has been string-matched
back into the source page text. Unverified fields are not shown as values.
No confidence percentages appear anywhere in the UI.

## Consequences

- Recall drops. Some fields present in documents will be missed because the
  model paraphrased instead of quoting. Accepted.
- Extraction costs an extra verification pass. Cheap — it is string matching.
- The product claim becomes defensible rather than aspirational.
