# CIRP Index

A searchable, evidence-linked index of Indian insolvency (IBC) orders published by the Insolvency and Bankruptcy Board of India (IBBI). Every structured fact shown to a user must be traceable to a verbatim span in a source order PDF.

## Setup

```bash
# Start Postgres database with pg_trgm
docker compose up -d

# Backend setup & migrations
cd backend
pip install -e ".[dev]"
alembic upgrade head

# Frontend setup
cd ../frontend
npm install
```

## Verify

```bash
cd backend
pytest -q
ruff check . && ruff format --check .
mypy .

cd ../frontend
npm run typecheck
npm run lint
npm run build
```

## Run

```bash
# API server (port 8000)
cd backend && uvicorn app.main:app --reload

# UI server (port 5173)
cd frontend && npm run dev
```

## Mandatory UI Disclaimer

"Orders are facilitation copies sourced from the public IBBI order listing and are not certified copies issued by any judicial authority. Verify against the original before relying on any figure."
