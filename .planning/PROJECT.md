# PROJECT

## Name
Polymarket Bot

## Current State
Shipped version: v1.0

The project now provides a research-grade, paper-only Polymarket system with live snapshot ingestion, replay workflows, explainable relationship inference, segment analytics, trade lifecycle tracking, and snapshot backfill support.

## Next Milestone Goals
- semi-live validation tooling
- richer order book / fill realism
- promotion gating for validated segments
- operator-facing review workflow

<details>
<summary>Archived v1.0 project context</summary>

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

</details>
