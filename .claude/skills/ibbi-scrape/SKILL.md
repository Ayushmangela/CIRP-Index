---
name: ibbi-scrape
description: Fetch and parse IBBI order listing pages. Use when writing or fixing the listing scraper, adding a new IBBI listing type (NCLAT, Supreme Court, High Court), debugging parse failures, or investigating rate-limit and blocking issues.
---

# IBBI scraping

Read docs/DATA_SOURCE.md first. It has the observed table shape, case number
formats and remark values.

## Always fetch before you parse

Never write a parser against an assumed HTML structure. Fetch one page, print
the relevant fragment, confirm the columns, then write the parser. Government
sites change markup without notice.

## Access rules — enforced, not aspirational

- One request per 2 seconds. Single connection. No parallelism, ever.
- `User-Agent: CIRPIndex/0.1 (research project; contact@example.com)`
- Exponential backoff on 5xx, 4 attempts, then record a failure and move on
- Never rotate IP or user agent to get around throttling

## Testing

Tests run against saved HTML fixtures in `backend/tests/fixtures/ibbi/`, never
the live site. Keep at least three fixtures from different points in the
pagination range — early pages and page 1000+ differ in formatting.

When adding a new listing type, add a fixture for it before writing the parser.

## Parse rules

- `subject_raw` is stored untouched, always
- Case number extraction lives in `parsing/case_number.py` as pure functions
  with tests, not inline in the scraper
- Remark to outcome mapping is an explicit dictionary. Unmapped values become
  `unclassified` and are logged with the raw string so the dictionary can grow.
- Deduplicate on `pdf_url`, and separately verify `pdf_sha256` on download

## Report after every run

Pages scanned, rows found, rows new, case numbers parsed as a percentage, and
every unmapped remark string. Write it to `ingestion_runs`.
