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
Frontend: Next.js (App Router) + TypeScript, TanStack Query, Tailwind
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
