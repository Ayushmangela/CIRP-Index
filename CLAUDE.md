# CLAUDE.md

@AGENTS.md

Everything above applies. Claude Code specifics below.

## Session start

Read AGENTS.md. Do not read the whole `docs/` tree — open only the doc the
task table points to. Reading everything burns context you will need later.

## Use plan mode for

- Any change touching `models/` or `alembic/`
- Any change to the extraction contract or the span verifier
- Anything spanning more than three files

Propose, wait for approval, then execute.

## Subagents

Fork exploration to a subagent. "Go read `ingestion/` and tell me how
deduplication works" pollutes the main context if run inline. Implementation
stays in the main thread where I can see it.

## Skills in this repo

- `/span-verify` — verify or debug the extraction span-matching rule
- `/ibbi-scrape` — fetch and parse IBBI listing pages safely
- `/run-eval` — run the gold-set accuracy report and interpret it

## When you disagree with the spec

Say so in your response, then implement what the spec says. Do not silently
substitute your judgement. If the spec is wrong I want to fix the spec, not
discover the drift three prompts later.

## Definition of done

Not "the code is written." It is: tests pass, mypy clean, the failure path is
handled explicitly, and any fact the UI displays has retrievable evidence
behind it.
