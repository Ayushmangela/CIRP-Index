# AGENTS.md — CIRP Index

Canonical agent instructions. Every coding agent reads this file.
Keep under 200 lines. Every rule here must be falsifiable — if you cannot
tell whether a rule was violated by looking at a diff, it does not belong here.

## What this project is

A searchable, evidence-linked index of Indian insolvency (IBC) orders published
by the Insolvency and Bankruptcy Board of India. Every structured fact shown to
a user must be traceable to a verbatim span in a source order PDF.

## Setup

```bash
docker compose up -d              # Postgres 16 with pg_trgm
cd backend && uv sync             # or: pip install -e ".[dev]"
alembic upgrade head
cd frontend && npm install
```

## Verify — run these before claiming any task is done

```bash
cd backend
pytest -q                         # must pass
ruff check . && ruff format --check .
mypy .                            # must be clean, no new ignores

cd frontend
npm run typecheck
npm run lint
npm run build
```

## Run

```bash
cd backend && uvicorn app.main:app --reload      # API on :8000
cd frontend && npm run dev                        # UI on :3000

python -m ingestion.ibbi_listing --start-page 0 --end-page 5
python -m ingestion.pdf_pipeline --limit 50
python -m extraction.run --limit 20
python -m eval.report
```

## Architecture map

```
backend/
  app/            FastAPI routes, dependency wiring
  models/         SQLAlchemy 2.x models — mirror docs/SCHEMA.md exactly
  ingestion/      IBBI listing scraper, PDF download, text extraction
  parsing/        Pure functions. indian_numbers.py, case_number.py
  extraction/     LLM client, prompt, Pydantic contract, span verifier
  linking/        Order -> case entity resolution
  eval/           Gold set harness and accuracy reporting
frontend/
  app/            Next.js App Router — three screens only: search, case
                  detail, bench analytics
  src/components/ Shared UI
  src/lib/api.ts  Generated types from the OpenAPI schema
```

## Non-negotiable rules

1. **Span verification is mandatory.** Every LLM-extracted field carries a
   verbatim quote and a page number. Normalise whitespace, string-match the
   quote against that page's stored text, and if it does not match, set
   `verified = false` and store no value. Never persist an unverified field as
   fact. See docs/EXTRACTION_CONTRACT.md.
2. **The LLM never does arithmetic on money.** It returns the literal string
   from the document. `parsing/indian_numbers.py` converts it.
3. **Never guess an enum.** Unmapped IBBI remark strings become
   `outcome = 'unclassified'` and get logged. No fuzzy matching on outcomes.
4. **Fuzzy name matching never auto-links.** It writes to the review queue with
   a similarity score. A human promotes it.
5. **No bare `except:`.** Every failure path gets a distinct status value and a
   log line naming what failed.
6. **PDFs are not persisted.** Store `source_url`, sha256, and extracted text.
7. **Rate limits are hard.** IBBI: 1 request per 2 seconds, single connection,
   descriptive User-Agent with contact email. LLM: max 3 concurrent, backoff
   with jitter on 429.
8. **Schema changes require a migration and a spec update.** Editing a model
   without an Alembic revision is a broken change.

## Boundaries — do not touch

- `docs/SCHEMA.md`, `docs/EXTRACTION_CONTRACT.md` — propose changes in your
  response, do not edit them yourself
- `backend/eval/gold_labels/` — human-labelled ground truth, never regenerate
- `.env`, `.env.local` — read `.env.example` instead
- `alembic/versions/` — never edit an applied migration, add a new one
- Never scrape NSE, BSE, MCA, eCourts, or Indian Kanoon. Their terms prohibit
  it or they charge per document. IBBI only.

## Conventions

- Python 3.11, SQLAlchemy 2.x style (`Mapped[]`, no legacy Query API)
- Pydantic v2 on every API boundary. No raw dicts crossing a module edge.
- `Decimal` for money, never `float`
- All datetimes timezone-aware UTC in the DB; format for display in the UI only
- React function components with hooks. No class components.
- TanStack Query for all server state. No `useEffect` fetching.
- Tailwind utility classes. No CSS-in-JS, no styled-components.

## Deeper docs — read on demand, not by default

| Doing this | Read this first |
|---|---|
| Scraper or ingestion work | docs/DATA_SOURCE.md |
| LLM extraction or verification | docs/EXTRACTION_CONTRACT.md |
| Any model or migration | docs/SCHEMA.md |
| Any UI work | docs/DESIGN_SYSTEM.md |
| Accuracy, gold set, metrics | docs/EVALUATION.md |
| Wondering why something is the way it is | docs/decisions/ |

## Mistakes made before — do not repeat

- Assuming the IBBI table shape without fetching a page first. Fetch, inspect,
  then write the parser.
- "Improving" the schema mid-build. The schema is fixed. Propose, don't act.
- Tuning the extraction prompt until the rejection rate looks good. A high
  rejection rate is information about the documents, not a bug to hide.
- Adding a fourth screen. There are three screens. Widening scope before the
  gold set exists is how this project dies.
