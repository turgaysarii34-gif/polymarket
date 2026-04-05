# polymarket-bot

MVP foundation for detecting cross-market pricing inconsistencies on Polymarket, simulating paper trades, and recording analytics for edge discovery.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install .
```

## Run fixture pipeline

```bash
PYTHONPATH=src python -m polymarket_bot.cli run-fixture-pipeline --fixture-path tests/fixtures/raw_markets.json --db-path analytics.db
```

## Current MVP scope
- fixture-based ingestion
- canonical market normalization
- relationship inference
- rule-based opportunity scoring
- risk filtering
- paper trade simulation
- sqlite analytics persistence

## Out of scope
- live trading
- dashboards
- machine learning
- news ingestion
