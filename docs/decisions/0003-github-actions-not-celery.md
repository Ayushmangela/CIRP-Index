# 0003 — GitHub Actions for ingestion instead of a worker queue

**Status:** accepted
**Date:** 2026-08-12

## Context

The reference architecture for this kind of pipeline is Celery plus Redis plus
an always-on worker. No free hosting tier offers a persistent background worker;
they require a paid instance. Meanwhile the actual job is a once-daily batch
bounded by an external LLM quota, not a high-throughput queue.

## Decision

Ingestion runs as a scheduled GitHub Actions workflow. It reads a watermark from
`ingestion_runs`, works until the daily LLM budget is spent, writes a new
watermark, and exits cleanly. A partial run is a success.

## Consequences

- Zero infrastructure cost, free logs, free retries, free secret management.
- No sub-daily latency. Fine — orders are published in daily batches.
- Resumability must be correct, because every run is expected to be partial.
