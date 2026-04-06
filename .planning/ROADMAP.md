# ROADMAP

## Milestone: Research-grade paper trading system

### Phase 1 — MVP foundation [completed]
Build canonical schema, relationship v1, signal scoring, risk filters, paper execution v1, analytics v1, and fixture pipeline.

### Phase 2 — Real ingestion replay pipeline [completed]
Add live Polymarket client, snapshot save/load, freshness handling, snapshot metadata, replay pipeline, and snapshot CLI workflows.

### Phase 3 — Relationship engine v2 [completed]
Improve market linking with stronger same-theme heuristics, explicit relation evidence payloads, and better confidence/risk scoring.

### Phase 4 — Segment analytics [completed]
Add category/theme/relation-type summaries and false-positive review views so research can rank strategy slices.

### Phase 5 — Paper execution lifecycle v2 [completed]
Add hold windows, exit evaluation, closed-trade persistence, and basic realized paper PnL measurement.

### Phase 6 — Snapshot backfill runner [completed]
Run research pipeline over many saved snapshots and persist batch results for longitudinal analysis.
