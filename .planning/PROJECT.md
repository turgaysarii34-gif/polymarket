# PROJECT

## Name
Polymarket Bot

## Objective
Build a research-grade, profit-seeking Polymarket trading system that discovers cross-market pricing inconsistencies, paper trades them honestly, and narrows toward only evidence-backed strategy segments before any live automation.

## Current status
Completed phases:
1. MVP foundation: canonical normalization, relationship inference v1, signal scoring, risk filters, paper execution, analytics, fixture pipeline.
2. Real ingestion replay pipeline: Polymarket client boundary, snapshot storage, freshness handling, snapshot metadata persistence, replay/live snapshot CLI workflows.

## Product boundaries
- No live trading yet.
- No full auto live execution.
- No ML-heavy forecasting.
- No news parsing.

## Current priority
Advance from raw ingestion and replayability to research usefulness: richer relationship quality, segment-aware analytics, improved paper-trade lifecycle realism, and evidence-producing backfill workflows.
