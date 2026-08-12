# CIRP Index — Agent Build Plan

Two things live in this document:

1. **PROJECT_SPEC.md** — save this as a file in your repo root. Every prompt below tells the agent to read it first. This is what keeps decisions stable across sessions.
2. **Nine sequential prompts** — paste one at a time into Claude Code. Each has exit criteria. Do not move to the next prompt until the current one's criteria pass.

---

# PART 1 — PROJECT_SPEC.md

Save the block below verbatim as `PROJECT_SPEC.md` in your repo root before running any prompt.

```markdown
# CIRP Index — Project Specification

## What this is
A searchable, evidence-linked index of Indian insolvency (IBC) orders published
by the Insolvency and Bankruptcy Board of India. Every structured fact displayed
must be traceable to a verbatim span in a source order PDF.

## Non-goals
- No investment advice, no credit scoring, no company "health scores"
- No prediction of case outcomes
- No claim that our copies are certified copies
- No scraping of NSE, BSE, MCA, eCourts, or Indian Kanoon

## Source of truth
IBBI public order listing: https://www.ibbi.gov.in/en/orders/nclt
Paginated HTML table. Columns: Orders Date, Subject (matter name + case number),
Orders (PDF link with file size), Remarks (outcome label).
Pagination via `?page=N`, zero-indexed, runs past page 1400.

Related listings on the same site (add later, same parser shape):
`/en/orders/nclat`, `/en/orders/supreme-court`, `/en/orders/high-court`

## Hard constraints
- Free tier only. No paid API, no paid hosting, no paid data.
- LLM: Gemini Flash / Flash-Lite free tier. Assume ~15 RPM and a daily request
  cap that varies — read the live limit from AI Studio, never hardcode it.
- Postgres: Neon or Supabase free tier (NOT Render — its free Postgres is
  deleted after 30 days).
- No Celery, no Redis worker, no always-on background process. Ingestion runs
  as a GitHub Actions scheduled workflow.
- Do not store PDFs long-term. Store source_url + extracted text + sha256 hash.

## Rate limiting rules (non-negotiable)
- IBBI requests: max 1 request per 2 seconds, single connection, retry with
  exponential backoff on 5xx, descriptive User-Agent with a contact email.
- LLM: token-bucket limiter, respect 429 with backoff + jitter, never parallel
  fire more than 3 requests.

## Extraction contract
The LLM returns JSON only. Every extracted field carries an `evidence` object:

{
  "field": "claim_amount",
  "value": 26420000,
  "unit": "INR",
  "evidence": {
    "quote": "verbatim text from the order, 10-40 words",
    "page": 4
  },
  "extraction_method": "llm"
}

**Span verification is mandatory.** After each extraction, normalise whitespace
and string-match `evidence.quote` against the text of the cited page. If the
quote is not found, discard the field and mark it `unverified`. Never persist an
unverified field as fact. This rule is the product.

## Indian number parsing (own module, unit tested)
Must correctly handle all of these:
- Indian digit grouping: "1,24,56,000" -> 12456000
- "Rs. 26.42 lakhs" -> 2642000
- "Rs. 5,000 crore" / "₹5000 Cr" -> 50000000000
- "Rs. 26,42,000/-" -> 2642000
- Table-level scale footnotes ("all figures in lakhs unless otherwise stated")
Never let the LLM do arithmetic on money. It returns the literal string; this
module converts.

## Outcome taxonomy
Derive from the IBBI Remarks column, normalised into an enum. Observed raw
values include: Admitted, Liquidation, Dissolution, Cirp-withdrawn,
12a-withdrawn, Others, Appointment Of Rp In Pg Case, Others In Pg Case.
Store BOTH `remarks_raw` (exact source string) and `outcome` (normalised enum).
Unmapped raw values go to `outcome = 'unclassified'` — never guess.

Enum: admitted | cirp_ongoing | resolution_approved | liquidation |
dissolved | withdrawn | unclassified

## Database schema

orders
  id, order_date, subject_raw, case_number, bench, pdf_url, pdf_sha256,
  file_size_bytes, remarks_raw, outcome, page_count, is_scanned,
  processing_status, retrieved_at, source_listing_page

order_pages
  id, order_id, page_number, text

cases
  id, canonical_case_number, corporate_debtor_name, bench, first_order_date,
  latest_order_date, current_outcome

case_aliases
  id, case_id, alias_text, alias_type   -- entity resolution lives here

extracted_fields
  id, order_id, case_id, field_name, value_text, value_numeric, value_date,
  unit, confidence_source, verified, extraction_method, model_name,
  extracted_at

evidence
  id, extracted_field_id, order_id, page_number, quote, char_start, char_end

gold_labels
  id, order_id, field_name, expected_value, labelled_by, labelled_at

ingestion_runs
  id, started_at, finished_at, pages_scanned, orders_found, orders_new,
  orders_processed, orders_failed, llm_calls, notes

Indexes: orders(order_date), orders(outcome), orders(bench),
extracted_fields(case_id, field_name), cases(corporate_debtor_name) with
pg_trgm for fuzzy search.

## Fields to extract per order
corporate_debtor, applicant_creditor, creditor_type (financial/operational/
corporate_applicant), claim_amount, section_invoked, resolution_professional,
adjudicating_authority_bench, admission_date, order_type

## Tech stack
Backend: Python 3.11, FastAPI, SQLAlchemy 2.x, Pydantic v2, httpx, pypdf +
pdfplumber, tenacity
Frontend: React + Vite + TypeScript, TanStack Query, Tailwind
DB: PostgreSQL + pg_trgm
Jobs: GitHub Actions cron
Deploy: Vercel (frontend), Render/Fly free web service (API), Neon (DB)

## Design system
Background #FAF9F6, text #1A1A1A, 1px warm grey hairlines, accent deep ink
blue. Sans-serif UI, monospace for case numbers / dates / rupee amounts.
Flat status pills with 1px borders. No gradients, no shadows, no rounded card
stacks. Dense, editorial, archival — a research instrument, not a SaaS
dashboard.

Outcome colours: admitted slate blue · cirp_ongoing amber · resolution_approved
deep green · liquidation rust red · dissolved warm grey · withdrawn muted lilac

## Mandatory UI disclaimer
Footer on every page, small italic muted grey:
"Orders are facilitation copies sourced from the public IBBI order listing and
are not certified copies issued by any judicial authority. Verify against the
original before relying on any figure."

## Definition of done for any feature
- Typed end to end (Pydantic on the wire, TypeScript on the client)
- Failure path handled explicitly, never a bare except
- Any displayed fact has retrievable evidence
- Tests for parsing and verification logic
```

---

# PART 2 — THE NINE PROMPTS

Run in order. Fresh context per prompt is fine and often better.

---

## Prompt 1 — Bootstrap

```
Read PROJECT_SPEC.md in full before writing anything.

Set up the project skeleton:
- Monorepo: /backend (Python) and /frontend (Vite React TS)
- Backend: FastAPI app, SQLAlchemy 2.x models for every table in the spec,
  Alembic with an initial migration, Pydantic v2 settings from env
- docker-compose.yml with Postgres 16 + pg_trgm extension enabled
- .env.example listing every variable, README with setup steps
- pytest configured with a test database fixture
- Ruff + mypy configured

Implement the models exactly as specified. Do not add tables, do not rename
columns, do not "improve" the schema. If something in the spec looks wrong,
say so in your response but implement it as written.

No scraping, no LLM code, no UI in this step.
```

**Exit criteria:** `docker compose up` runs, `alembic upgrade head` creates every table, `pytest` passes with zero tests, mypy clean.

---

## Prompt 2 — IBBI listing scraper

```
Read PROJECT_SPEC.md.

Build the IBBI order listing scraper as backend/ingestion/ibbi_listing.py.

Requirements:
- Fetch https://www.ibbi.gov.in/en/orders/nclt?page=N with httpx
- Respect the rate limiting rules in the spec exactly
- Parse the HTML table into: order_date, subject_raw, pdf_url,
  file_size_bytes, remarks_raw
- From subject_raw, extract case_number with a regex module that handles the
  observed formats: CP(IB) No. 155/9/HDB/2020, IA(IBC)-66-2022,
  I.A. No. 4692 of 2021 in C.P. No. (IB)-1644 (PB)-2018,
  CP(IBC)-24(KOB)-2021. Keep subject_raw untouched.
- Map remarks_raw to the outcome enum via an explicit dictionary. Unmapped
  values become 'unclassified' and are logged. Do not use fuzzy matching.
- Upsert into orders, deduplicating on pdf_url
- Record every run in ingestion_runs
- A CLI: python -m ingestion.ibbi_listing --start-page 0 --end-page 5

Write tests against saved HTML fixtures, not the live site. Save 3 fixture
pages from different points in the pagination range.

Before you write the parser, fetch one page and show me the actual HTML
structure. Do not assume the table shape.
```

**Exit criteria:** 5 pages scraped, ~125 rows in `orders`, case_number populated on >90% of rows, every unmapped remark logged.

---

## Prompt 3 — PDF acquisition and text extraction

```
Read PROJECT_SPEC.md.

Build backend/ingestion/pdf_pipeline.py.

Pipeline per order:
1. Download the PDF to a temp file, compute sha256, skip if hash already seen
2. Detect scanned vs digital: if extractable text is under 100 characters per
   page averaged across the document, mark is_scanned = true
3. For digital PDFs: extract per-page text with pdfplumber, preserving page
   numbers, write one row per page into order_pages
4. Normalise whitespace but preserve line breaks — the span verification in
   the next step depends on stable text
5. Delete the temp PDF. Never persist the file.
6. Set processing_status: text_extracted | scanned_skipped | failed

Scanned orders are SKIPPED for now, not OCR'd. Record them so we can count
them. Report what percentage of the sample is scanned when you're done.

Add a CLI: python -m ingestion.pdf_pipeline --limit 50

Handle: 404s, timeouts, password-protected PDFs, zero-byte responses,
HTML error pages served with a .pdf URL. Each gets a distinct status, not a
generic failure.
```

**Exit criteria:** 50 orders processed, page text in `order_pages`, scanned percentage reported, no unhandled exceptions in the log.

---

## Prompt 4 — Indian number parser

```
Read PROJECT_SPEC.md, the Indian number parsing section.

Build backend/parsing/indian_numbers.py as a pure function module with no
LLM involvement.

parse_amount(text: str, scale_hint: str | None = None) -> Decimal | None

Must handle every case listed in the spec, plus:
- "Rupees Twenty Six Lakh Forty Two Thousand only" (words to number)
- Mixed: "Rs. 26.42 lakhs (Rupees Twenty Six Lakh Forty Two Thousand)"
- Negative and bracketed negatives: "(1,24,000)"
- Absent or malformed input returns None, never raises, never guesses

Write at least 30 unit tests covering these. This module must be bulletproof
before any LLM extraction depends on it. Show me the test output.
```

**Exit criteria:** 30+ tests, all passing. Deliberately try to break it before moving on.

---

## Prompt 5 — LLM extraction with span verification

```
Read PROJECT_SPEC.md, the extraction contract section. This is the most
important prompt in the build — the span verification rule is the product.

Build backend/extraction/.

1. A Pydantic v2 model matching the extraction contract exactly, with an
   evidence object required on every field.
2. A Gemini client with: token-bucket rate limiting, 429 backoff with jitter,
   JSON-only response mode, retry on malformed JSON up to 2 times.
3. A prompt that takes the order's page text (chunked if over context) and
   returns the fields listed in the spec. The prompt must instruct the model
   to return a VERBATIM quote for each field and the page number it came from.
4. A verifier: normalise whitespace on both sides, then string-match the quote
   against order_pages.text for the cited page. On match, store char_start and
   char_end in evidence and set verified = true. On no match, try the adjacent
   pages. On still no match, set verified = false and DO NOT store a value.
5. Route all money fields through parsing.indian_numbers. The LLM returns the
   literal string only; it never does arithmetic.
6. Persist to extracted_fields + evidence. Log llm_calls to ingestion_runs.

Report, for a 20-order sample: fields attempted, fields verified, fields
rejected by the verifier, and the rejection reasons grouped.

If the rejection rate is above 25%, stop and tell me — do not tune the prompt
to make the number look better. A high rejection rate is information about the
documents, not a bug to hide.
```

**Exit criteria:** 20 orders extracted, verified/rejected counts reported, rejection reasons grouped and readable.

---

## Prompt 6 — Gold set and accuracy harness

```
Read PROJECT_SPEC.md.

Build the evaluation harness. This exists so the README can state a real
accuracy number instead of "it seems to work".

1. A CLI that picks 25 orders stratified across at least 4 different benches
   and 4 different outcomes, and dumps them into a labelling worksheet
   (CSV + the page text alongside) for me to fill in by hand.
2. An importer that loads my completed worksheet into gold_labels.
3. An evaluator: per field name, compute exact-match accuracy, and for numeric
   fields also within-1% accuracy. Output a table to stdout and a JSON report
   to /eval/latest.json.
4. Track: field precision (of the fields we claimed, how many were right) and
   field recall (of the fields present in the document, how many we found).
   Report both. They are different failure modes.

Do not populate gold_labels yourself. Do not let the model label its own
homework — the whole point is that a human filled it in.
```

**Exit criteria:** worksheet generated, you hand-label 25 orders (6–10 hours, unavoidable), evaluator prints a real accuracy table.

---

## Prompt 7 — Case linking

```
Read PROJECT_SPEC.md.

Multiple orders belong to one insolvency case. Build backend/linking/.

Link orders into cases using, in priority order:
1. Exact case_number match after normalisation (strip spaces, punctuation,
   unify CP(IB)/C.P.(IB)/CP IB)
2. "in" clause parsing: "IA No. 4692 of 2021 in C.P. No. (IB)-1644 (PB)-2018"
   links the IA to the parent CP
3. Corporate debtor name fuzzy match within the same bench, using pg_trgm,
   threshold 0.85, ONLY as a candidate suggestion

Rule 3 never auto-links. It writes a row to a review queue table with the
similarity score. Manual confirmation promotes it and writes a case_aliases
row. Entity resolution that silently merges two different companies is worse
than no linking at all.

Derive cases.current_outcome from the most recent order in the case by date,
not by insertion order.

Report: cases created, orders linked by each rule, orders left unlinked,
candidates sitting in the review queue.
```

**Exit criteria:** cases populated, unlinked count reported, review queue has entries and nothing was auto-merged by fuzzy match.

---

## Prompt 8 — API and frontend

```
Read PROJECT_SPEC.md, including the design system and the mandatory
disclaimer.

Backend endpoints:
  GET /api/v1/cases?q=&outcome=&bench=&year=&min_amount=&page=&page_size=
  GET /api/v1/cases/{id}
  GET /api/v1/cases/{id}/orders
  GET /api/v1/orders/{id}
  GET /api/v1/orders/{id}/evidence
  GET /api/v1/stats/benches
  GET /api/v1/stats/outcomes-by-year
All paginated, all Pydantic response models, all with OpenAPI descriptions.

Frontend — exactly three screens, no more:

1. Search results. Left filter sidebar (outcome with counts and colour
   squares, bench, section, year, amount range). Dense table: date, corporate
   debtor, case number, bench, claim amount right-aligned, outcome pill.
   Active filter chips above. Monospace pagination below.

2. Case detail. Header with debtor name, case number, metadata chips, outcome
   badge right-aligned. Horizontal timeline strip of the case's orders.
   Two-column body: left is extracted fields as label-value rows with hairline
   dividers and a superscript source marker; right is the evidence panel
   showing the quoted span with page number. Clicking a field's marker
   scrolls the evidence panel to that quote.

3. Bench analytics. Four flat stat tiles, a horizontal bar chart of median
   duration by bench, a stacked area chart of outcome mix by year.

Apply the design system strictly. Monospace for case numbers, dates, amounts.
Flat pills. Hairlines not cards. No shadows, no gradients.

The evidence panel is the whole point of this product. Build it first and
build it well.
```

**Exit criteria:** all three screens render against real data, evidence panel scroll-to-quote works, disclaimer visible on every page.

---

## Prompt 9 — Deploy and document

```
Read PROJECT_SPEC.md.

1. GitHub Actions workflow, daily cron:
   - Scrape new listing pages since last run (read watermark from
     ingestion_runs)
   - Process new PDFs
   - Run extraction until the daily LLM budget is spent, then exit cleanly
     with a resume watermark — a partial run is a success, not a failure
   - Post a summary to the run log
   - Secrets from GitHub Secrets, never committed

2. Deploy: frontend to Vercel, API to a free web service, DB on Neon. Document
   the cold-start behaviour honestly in the README.

3. README with:
   - What it does and who it's for
   - The evidence-first architecture explained, with the span verification
     rule stated plainly
   - Real accuracy numbers from /eval/latest.json, including what we get wrong
   - Data source, IBBI disclaimer, what this is not
   - Known limitations: scanned orders skipped and the percentage, unlinked
     cases count, unclassified outcomes count
   - Local setup

Write the limitations section honestly. A README that admits the scanned-order
gap is more credible than one that doesn't mention it.
```

**Exit criteria:** cron runs green on schedule, live URL works, README has real numbers in it.

---

# Working notes

**Order matters for one reason.** Prompts 2–5 build the ingestion pipeline. Start it running as soon as prompt 5 passes, because the corpus takes 6–15 days to churn through the free LLM quota regardless of how fast you code. Build prompts 6–8 while it runs. Doing it the other way round adds two dead weeks at the end.

**When the agent drifts,** paste this: *"Re-read PROJECT_SPEC.md. You changed [X] from what the spec says. Revert it or tell me why the spec is wrong."* Drift on the schema and the span verification rule is the failure mode that costs the most to unwind.

**Do not skip prompt 6.** Every AI-built project in a portfolio looks similar. A hand-labelled gold set and an honest accuracy table is the thing that makes yours look like engineering rather than assembly.
