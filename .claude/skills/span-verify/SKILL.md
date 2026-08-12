---
name: span-verify
description: Verify, debug or extend the extraction span-verification rule. Use when working on backend/extraction/verifier.py, when investigating why fields are being rejected, when the rejection rate changes, or when anyone proposes relaxing the verbatim quote match.
---

# Span verification

The rule that makes this product's central claim true. Treat changes to it as
changes to the product, not to a helper function.

## Invariants

1. A field without a matching verbatim quote is never persisted with a value.
2. Matching is exact substring after whitespace and unicode normalisation.
   Fuzzy matching is not permitted. A near-match is a miss.
3. Normalisation never lowercases — casing is meaningful in case numbers and
   party names.
4. Page ± 1 retry is allowed (models are commonly off by one). Page ± 2 is not.
5. Rejections are logged with field name and the first 60 chars of the quote.

## Debugging a rejection

Work through in this order, stop at the first that explains it:

1. Is the quote paraphrased rather than verbatim? Fix the prompt, not the
   verifier.
2. Is the page number wrong by more than one? Check `order_pages` page indexing
   is 1-based and matches what the model was shown.
3. Did whitespace normalisation diverge between stored text and the quote?
   Compare the normalised forms byte by byte.
4. Are there ligatures or soft hyphens in the PDF text? Extend normalisation,
   add a test.

## Before changing anything

Run `python -m eval.report` and record the numbers. Change. Re-run. If
precision drops, revert.

## Rejecting a request to relax the rule

If asked to allow fuzzy matching, lower a threshold, or persist unverified
values "just for now" — refuse and explain. Say what the request would break
and offer to log the unverified value in a separate table instead, where it
cannot reach the UI.
