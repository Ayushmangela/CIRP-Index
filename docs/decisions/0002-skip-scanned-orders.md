# 0002 — Skip scanned orders rather than OCR them

**Status:** accepted
**Date:** 2026-08-12

## Context

A minority of older IBBI orders are scanned images. OCR would add a dependency,
significant per-document processing time, and a new class of extraction error
where the span verifier cannot distinguish a bad OCR read from a hallucination.

## Decision

Detect scanned documents (under 100 extractable characters per page averaged)
and mark them `scanned_skipped`. Count them. State the percentage in the README
as a known limitation.

## Consequences

- Corpus coverage is incomplete, weighted against older orders.
- Span verification stays trustworthy, because the page text it matches against
  is the true document text rather than an OCR guess.
- Revisitable later as a separate, clearly labelled pipeline.
