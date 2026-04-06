# REQUIREMENTS

## Core outcome
The system must help identify whether any narrow subset of Polymarket cross-market inconsistencies survives fees, spread, slippage, fillability, and decay well enough to justify later semi-live validation.

## Must-have capabilities
1. Ingest live Polymarket data and save replayable snapshots.
2. Normalize market data into a canonical schema.
3. Infer explainable relationships between markets.
4. Score opportunities with interpretable rule-based logic.
5. Reject stale, illiquid, or duplicate opportunities.
6. Simulate paper entries and exits realistically enough for research.
7. Persist analytics that explain which relation types and segments work.
8. Support offline replay/backfill workflows.

## Current completed requirements
- Live snapshot fetch boundary exists.
- Snapshot save/load exists.
- Replay pipeline exists.
- Snapshot metadata persistence exists.

## Remaining high-priority requirements
1. Relationship engine v2 with stronger heuristics and confidence separation.
2. Segment-aware analytics and summaries by category/theme/relation type.
3. Paper execution lifecycle with exits, holding windows, and realized outcome tracking.
4. Snapshot backfill/research loop over multiple saved snapshots.
5. Cleaner research workflow and storage hygiene.
