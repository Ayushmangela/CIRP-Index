# 0004 — OCR scanned orders, as a separate, clearly labelled pipeline

**Status:** accepted
**Date:** 2026-08-12
**Supersedes:** 0002

## Context

0002 chose to skip scanned orders entirely rather than OCR them, because
span verification exact-matches an LLM's quote against stored page text to
prove it isn't hallucinating. If the stored text were itself an OCR guess,
a "verified" field could still be wrong with no way to detect it — 0002
correctly named this as the central risk, and left the door open to
revisit "as a separate, clearly labelled pipeline."

That door is now being taken: OCR coverage is worth more than the
completeness gap costs, provided the OCR'd text never gets treated as
equivalent to real digital text anywhere in the system.

## Decision

- OCR runs as its own pipeline step (`ingestion/ocr_pipeline.py`), against
  orders already marked `scanned_skipped` — a live query, not a one-time
  backfill, so it also covers any future order that comes back scanned.
- PDFs are rasterized locally with `pymupdf` and read with `pytesseract`
  (`tesseract` binary); the PDF itself is still never persisted, per
  AGENTS.md rule 6.
- Orders that succeed land under a **new, distinct** `processing_status`:
  `ocr_extracted` — never `text_extracted`. Every downstream consumer
  (extraction's order-selection query, the API, the frontend) can tell OCR
  text apart from real-extracted text at all times.
- Span verification itself is unchanged: an OCR misread simply fails to
  match, the same way a hallucinated quote would. The rejection rate on
  OCR'd orders is expected to run higher than on real text, and that
  difference is reported, not hidden — it's the signal 0002 wanted
  preserved.
- The evidence panel and order timeline visibly flag `ocr_extracted`
  evidence with an "OCR" label pointing back to the source PDF, everywhere
  that evidence is shown.
- A page that OCRs to near-nothing is left `scanned_skipped`, not silently
  marked done with empty pages.

## Consequences

- Corpus coverage improves for older/scanned orders, at the cost of a
  real, measurable accuracy gap on that slice — visible in the rejection
  rate and in the UI, not averaged away.
- One more dependency (`pymupdf`, `pytesseract`) and per-document
  processing time, as 0002 anticipated.
- If OCR quality later proves too poor to be useful, the fix is to stop
  running `ocr_pipeline.py` and leave those orders `scanned_skipped` again
  — no data needs to be un-persisted, since `ocr_extracted` was never
  conflated with `text_extracted` in the first place.
