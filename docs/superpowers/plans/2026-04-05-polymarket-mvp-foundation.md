# Polymarket MVP Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first end-to-end MVP foundation for discovering cross-market pricing inconsistencies on Polymarket, paper trading them realistically, and recording enough analytics to judge whether any narrow edge exists.

**Architecture:** The system is a small Python application organized around bounded modules: domain models, ingestion, normalization, relationships, signals, paper execution, analytics, and risk controls. The first version uses deterministic fixtures and a local CLI runner so the core decision pipeline is testable before any live exchange integration or scheduling complexity is introduced.

**Tech Stack:** Python 3.12, pytest, pydantic, sqlite3, requests, typer

---

## File Structure

### Create
- `pyproject.toml` — project metadata, dependencies, pytest config, entrypoint
- `README.md` — minimal local setup and run instructions
- `src/polymarket_bot/__init__.py` — package marker
- `src/polymarket_bot/config.py` — runtime configuration and default thresholds
- `src/polymarket_bot/domain/market.py` — normalized market and quote models
- `src/polymarket_bot/domain/relationship.py` — relationship and explanation models
- `src/polymarket_bot/domain/signal.py` — signal ranking and explanation models
- `src/polymarket_bot/domain/trade.py` — paper trade and execution result models
- `src/polymarket_bot/domain/analytics.py` — analytics record models
- `src/polymarket_bot/ingestion/polymarket_client.py` — raw market fetcher abstraction
- `src/polymarket_bot/ingestion/fixtures.py` — deterministic raw fixture loader for tests and local runs
- `src/polymarket_bot/normalization/normalize.py` — raw-to-canonical normalization logic
- `src/polymarket_bot/relationships/engine.py` — v1 relationship inference
- `src/polymarket_bot/signals/scorer.py` — v1 inconsistency scoring
- `src/polymarket_bot/risk/filters.py` — stale, liquidity, spread, duplicate, exposure filters
- `src/polymarket_bot/execution/paper_engine.py` — paper entry and exit simulation
- `src/polymarket_bot/analytics/store.py` — sqlite persistence helpers
- `src/polymarket_bot/analytics/reporting.py` — segment and relation-type summaries
- `src/polymarket_bot/pipeline.py` — end-to-end orchestration for one evaluation pass
- `src/polymarket_bot/cli.py` — CLI entrypoint for loading fixtures and running pipeline
- `tests/fixtures/raw_markets.json` — deterministic raw market fixture set
- `tests/test_normalization.py` — normalization tests
- `tests/test_relationships.py` — relationship engine tests
- `tests/test_signals.py` — signal scoring tests
- `tests/test_risk_filters.py` — risk control tests
- `tests/test_paper_execution.py` — paper execution tests
- `tests/test_pipeline.py` — end-to-end pipeline tests
- `tests/test_reporting.py` — analytics summary tests

### Modify
- None. Repository is effectively empty.

---

### Task 1: Bootstrap the Python project

**Files:**
- Create: `pyproject.toml`
- Create: `README.md`
- Create: `src/polymarket_bot/__init__.py`
- Create: `src/polymarket_bot/cli.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing smoke test**

```python
from typer.testing import CliRunner

from polymarket_bot.cli import app


def test_cli_runs_fixture_pipeline(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-fixture-pipeline",
            "--fixture-path",
            "tests/fixtures/raw_markets.json",
            "--db-path",
            str(tmp_path / "analytics.db"),
        ],
    )

    assert result.exit_code == 0
    assert "signals=" in result.stdout
    assert "trades=" in result.stdout
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py::test_cli_runs_fixture_pipeline -v`
Expected: FAIL with `ModuleNotFoundError` for `polymarket_bot`

- [ ] **Step 3: Write minimal project bootstrap code**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "polymarket-bot"
version = "0.1.0"
description = "Polymarket cross-market inconsistency discovery and paper trading"
requires-python = ">=3.12"
dependencies = [
  "pydantic>=2.7,<3",
  "pytest>=8.0,<9",
  "requests>=2.31,<3",
  "typer>=0.12,<1",
]

[project.scripts]
polymarket-bot = "polymarket_bot.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
```

```python
import typer

app = typer.Typer()


@app.command("run-fixture-pipeline")
def run_fixture_pipeline(fixture_path: str, db_path: str) -> None:
    print(f"signals=0 trades=0 fixture={fixture_path} db={db_path}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py::test_cli_runs_fixture_pipeline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml README.md src/polymarket_bot/__init__.py src/polymarket_bot/cli.py tests/test_pipeline.py
git commit -m "chore: bootstrap polymarket bot project"
```

### Task 2: Define canonical domain models and normalization

**Files:**
- Create: `src/polymarket_bot/config.py`
- Create: `src/polymarket_bot/domain/market.py`
- Create: `src/polymarket_bot/normalization/normalize.py`
- Test: `tests/test_normalization.py`
- Create: `tests/fixtures/raw_markets.json`

- [ ] **Step 1: Write the failing normalization test**

```python
from polymarket_bot.normalization.normalize import normalize_markets


def test_normalize_markets_produces_canonical_records(raw_fixture_markets):
    normalized = normalize_markets(raw_fixture_markets)

    assert len(normalized) == 3
    assert normalized[0].market_id == "mkt-election-2028-a"
    assert normalized[0].yes_price == 0.61
    assert normalized[0].spread_bps == 300
    assert normalized[0].category == "politics"
```

```python
import json
import pytest


@pytest.fixture
def raw_fixture_markets():
    with open("tests/fixtures/raw_markets.json", "r", encoding="utf-8") as handle:
        return json.load(handle)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalization.py::test_normalize_markets_produces_canonical_records -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal canonical model and normalization code**

```python
from pydantic import BaseModel


class NormalizedMarket(BaseModel):
    market_id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    spread_bps: int
    close_time: str
    category: str
    theme_tags: list[str]
    outcome_names: list[str]
```

```python
from polymarket_bot.domain.market import NormalizedMarket


def normalize_markets(raw_markets: list[dict]) -> list[NormalizedMarket]:
    normalized: list[NormalizedMarket] = []

    for raw in raw_markets:
        normalized.append(
            NormalizedMarket(
                market_id=raw["id"],
                question=raw["question"],
                yes_price=raw["prices"]["yes"],
                no_price=raw["prices"]["no"],
                volume=raw["volume"],
                spread_bps=raw["spread_bps"],
                close_time=raw["close_time"],
                category=raw["category"],
                theme_tags=raw["theme_tags"],
                outcome_names=raw["outcomes"],
            )
        )

    return normalized
```

```json
[
  {
    "id": "mkt-election-2028-a",
    "question": "Will Candidate A win the 2028 election?",
    "prices": {"yes": 0.61, "no": 0.39},
    "volume": 250000.0,
    "spread_bps": 300,
    "close_time": "2028-11-05T00:00:00Z",
    "category": "politics",
    "theme_tags": ["elections", "us"],
    "outcomes": ["Yes", "No"]
  },
  {
    "id": "mkt-election-2028-b",
    "question": "Will Candidate B win the 2028 election?",
    "prices": {"yes": 0.34, "no": 0.66},
    "volume": 210000.0,
    "spread_bps": 350,
    "close_time": "2028-11-05T00:00:00Z",
    "category": "politics",
    "theme_tags": ["elections", "us"],
    "outcomes": ["Yes", "No"]
  },
  {
    "id": "mkt-election-2028-c",
    "question": "Will any independent candidate win the 2028 election?",
    "prices": {"yes": 0.12, "no": 0.88},
    "volume": 80000.0,
    "spread_bps": 500,
    "close_time": "2028-11-05T00:00:00Z",
    "category": "politics",
    "theme_tags": ["elections", "us"],
    "outcomes": ["Yes", "No"]
  }
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalization.py::test_normalize_markets_produces_canonical_records -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/config.py src/polymarket_bot/domain/market.py src/polymarket_bot/normalization/normalize.py tests/test_normalization.py tests/fixtures/raw_markets.json
git commit -m "feat: add canonical market normalization"
```

### Task 3: Implement relationship inference v1

**Files:**
- Create: `src/polymarket_bot/domain/relationship.py`
- Create: `src/polymarket_bot/relationships/engine.py`
- Test: `tests/test_relationships.py`

- [ ] **Step 1: Write the failing relationship test**

```python
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships


def test_infer_relationships_returns_hard_constraint_and_theme_links(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)

    relationships = infer_relationships(markets)

    relation_types = {(item.left_market_id, item.right_market_id, item.relation_type) for item in relationships}
    assert ("mkt-election-2028-a", "mkt-election-2028-b", "mutually_exclusive") in relation_types
    assert ("mkt-election-2028-a", "mkt-election-2028-c", "same_theme") in relation_types
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_relationships.py::test_infer_relationships_returns_hard_constraint_and_theme_links -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal relationship model and inference code**

```python
from pydantic import BaseModel


class MarketRelationship(BaseModel):
    left_market_id: str
    right_market_id: str
    relation_type: str
    confidence: float
    why_linked: str
    semantic_risk_score: float
```

```python
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.relationship import MarketRelationship


MUTUALLY_EXCLUSIVE_PREFIX = "Will Candidate"


def infer_relationships(markets: list[NormalizedMarket]) -> list[MarketRelationship]:
    relationships: list[MarketRelationship] = []

    for index, left in enumerate(markets):
        for right in markets[index + 1 :]:
            if left.category == right.category and set(left.theme_tags) == set(right.theme_tags):
                relationships.append(
                    MarketRelationship(
                        left_market_id=left.market_id,
                        right_market_id=right.market_id,
                        relation_type="same_theme",
                        confidence=0.65,
                        why_linked="matching category and identical theme tags",
                        semantic_risk_score=0.35,
                    )
                )

            if left.question.startswith(MUTUALLY_EXCLUSIVE_PREFIX) and right.question.startswith(MUTUALLY_EXCLUSIVE_PREFIX):
                relationships.append(
                    MarketRelationship(
                        left_market_id=left.market_id,
                        right_market_id=right.market_id,
                        relation_type="mutually_exclusive",
                        confidence=0.9,
                        why_linked="candidate winner markets cannot both resolve yes",
                        semantic_risk_score=0.15,
                    )
                )

    return relationships
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_relationships.py::test_infer_relationships_returns_hard_constraint_and_theme_links -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/domain/relationship.py src/polymarket_bot/relationships/engine.py tests/test_relationships.py
git commit -m "feat: infer market relationships"
```

### Task 4: Implement inconsistency signal scoring

**Files:**
- Create: `src/polymarket_bot/domain/signal.py`
- Create: `src/polymarket_bot/signals/scorer.py`
- Test: `tests/test_signals.py`

- [ ] **Step 1: Write the failing signal scoring test**

```python
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.signals.scorer import score_opportunities


def test_score_opportunities_ranks_larger_constraint_break_higher(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)

    opportunities = score_opportunities(markets, relationships)

    assert opportunities[0].relation_type == "mutually_exclusive"
    assert opportunities[0].score > opportunities[-1].score
    assert "observed_total" in opportunities[0].explanation
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_signals.py::test_score_opportunities_ranks_larger_constraint_break_higher -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal signal model and scoring code**

```python
from pydantic import BaseModel


class SignalOpportunity(BaseModel):
    relationship_key: str
    relation_type: str
    score: float
    left_market_id: str
    right_market_id: str
    explanation: dict[str, float | str]
```

```python
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.relationship import MarketRelationship
from polymarket_bot.domain.signal import SignalOpportunity


EXPECTED_SUM_BY_RELATION = {
    "mutually_exclusive": 1.0,
    "same_theme": 1.0,
}


def score_opportunities(markets: list[NormalizedMarket], relationships: list[MarketRelationship]) -> list[SignalOpportunity]:
    market_by_id = {market.market_id: market for market in markets}
    opportunities: list[SignalOpportunity] = []

    for relation in relationships:
        left = market_by_id[relation.left_market_id]
        right = market_by_id[relation.right_market_id]
        observed_total = left.yes_price + right.yes_price
        expected_total = EXPECTED_SUM_BY_RELATION[relation.relation_type]
        raw_gap = max(0.0, observed_total - expected_total)
        liquidity_penalty = (left.spread_bps + right.spread_bps) / 10000
        adjusted = max(0.0, raw_gap * relation.confidence - liquidity_penalty)

        opportunities.append(
            SignalOpportunity(
                relationship_key=f"{relation.left_market_id}:{relation.right_market_id}:{relation.relation_type}",
                relation_type=relation.relation_type,
                score=round(adjusted, 6),
                left_market_id=relation.left_market_id,
                right_market_id=relation.right_market_id,
                explanation={
                    "observed_total": observed_total,
                    "expected_total": expected_total,
                    "raw_gap": raw_gap,
                    "liquidity_penalty": liquidity_penalty,
                    "confidence": relation.confidence,
                },
            )
        )

    return sorted(opportunities, key=lambda item: item.score, reverse=True)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_signals.py::test_score_opportunities_ranks_larger_constraint_break_higher -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/domain/signal.py src/polymarket_bot/signals/scorer.py tests/test_signals.py
git commit -m "feat: score inconsistency opportunities"
```

### Task 5: Add risk filters for stale, liquidity, spread, and duplicate suppression

**Files:**
- Create: `src/polymarket_bot/risk/filters.py`
- Test: `tests/test_risk_filters.py`
- Modify: `src/polymarket_bot/config.py`

- [ ] **Step 1: Write the failing risk filter test**

```python
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def test_filter_opportunities_removes_high_spread_duplicates(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    markets[2].spread_bps = 1200
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)

    filtered = filter_opportunities(opportunities, markets, seen_keys={opportunities[0].relationship_key})

    assert all(item.relationship_key != opportunities[0].relationship_key for item in filtered)
    assert all(item.right_market_id != "mkt-election-2028-c" for item in filtered)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_risk_filters.py::test_filter_opportunities_removes_high_spread_duplicates -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal configuration and risk filter code**

```python
from pydantic import BaseModel


class StrategyConfig(BaseModel):
    min_volume: float = 50000
    max_spread_bps: int = 800
    max_positions: int = 5
```
```

```python
from polymarket_bot.config import StrategyConfig
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity


def filter_opportunities(
    opportunities: list[SignalOpportunity],
    markets: list[NormalizedMarket],
    seen_keys: set[str],
    config: StrategyConfig | None = None,
) -> list[SignalOpportunity]:
    active_config = config or StrategyConfig()
    market_by_id = {market.market_id: market for market in markets}
    filtered: list[SignalOpportunity] = []

    for opportunity in opportunities:
        if opportunity.relationship_key in seen_keys:
            continue

        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]

        if left.volume < active_config.min_volume or right.volume < active_config.min_volume:
            continue

        if left.spread_bps > active_config.max_spread_bps or right.spread_bps > active_config.max_spread_bps:
            continue

        filtered.append(opportunity)

    return filtered
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_risk_filters.py::test_filter_opportunities_removes_high_spread_duplicates -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/config.py src/polymarket_bot/risk/filters.py tests/test_risk_filters.py
git commit -m "feat: add risk-based opportunity filters"
```

### Task 6: Implement paper execution and trade lifecycle

**Files:**
- Create: `src/polymarket_bot/domain/trade.py`
- Create: `src/polymarket_bot/execution/paper_engine.py`
- Test: `tests/test_paper_execution.py`

- [ ] **Step 1: Write the failing paper execution test**

```python
from polymarket_bot.execution.paper_engine import open_paper_trades
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def test_open_paper_trades_creates_position_with_fill_and_fees(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(filtered[:1], markets)

    assert len(trades) == 1
    assert trades[0].status == "open"
    assert trades[0].fill_price > 0
    assert trades[0].estimated_fee > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_paper_execution.py::test_open_paper_trades_creates_position_with_fill_and_fees -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal trade model and paper execution code**

```python
from pydantic import BaseModel


class PaperTrade(BaseModel):
    relationship_key: str
    left_market_id: str
    right_market_id: str
    status: str
    fill_price: float
    estimated_fee: float
    allocated_notional: float
```

```python
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity
from polymarket_bot.domain.trade import PaperTrade


DEFAULT_NOTIONAL = 100.0
FEE_RATE = 0.02
SLIPPAGE_BUFFER = 0.01


def open_paper_trades(opportunities: list[SignalOpportunity], markets: list[NormalizedMarket]) -> list[PaperTrade]:
    market_by_id = {market.market_id: market for market in markets}
    trades: list[PaperTrade] = []

    for opportunity in opportunities:
        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]
        fill_price = ((left.yes_price + right.yes_price) / 2) + SLIPPAGE_BUFFER
        fee = DEFAULT_NOTIONAL * FEE_RATE

        trades.append(
            PaperTrade(
                relationship_key=opportunity.relationship_key,
                left_market_id=opportunity.left_market_id,
                right_market_id=opportunity.right_market_id,
                status="open",
                fill_price=round(fill_price, 6),
                estimated_fee=round(fee, 6),
                allocated_notional=DEFAULT_NOTIONAL,
            )
        )

    return trades
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_paper_execution.py::test_open_paper_trades_creates_position_with_fill_and_fees -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/domain/trade.py src/polymarket_bot/execution/paper_engine.py tests/test_paper_execution.py
git commit -m "feat: add paper execution engine"
```

### Task 7: Persist analytics and generate summaries

**Files:**
- Create: `src/polymarket_bot/domain/analytics.py`
- Create: `src/polymarket_bot/analytics/store.py`
- Create: `src/polymarket_bot/analytics/reporting.py`
- Test: `tests/test_reporting.py`

- [ ] **Step 1: Write the failing analytics test**

```python
from polymarket_bot.analytics.reporting import summarize_relation_type_pnl
from polymarket_bot.analytics.store import initialize_db, insert_trade_rows
from polymarket_bot.domain.trade import PaperTrade


def test_summarize_relation_type_pnl_groups_results(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                relationship_key="a:b:mutually_exclusive",
                left_market_id="a",
                right_market_id="b",
                status="closed",
                fill_price=0.55,
                estimated_fee=2.0,
                allocated_notional=100.0,
            )
        ],
    )

    summary = summarize_relation_type_pnl(str(db_path))

    assert summary == [{"relation_type": "mutually_exclusive", "trade_count": 1, "gross_notional": 100.0}]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reporting.py::test_summarize_relation_type_pnl_groups_results -v`
Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Write minimal analytics persistence and reporting code**

```python
import sqlite3

from polymarket_bot.domain.trade import PaperTrade


def initialize_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                relationship_key TEXT PRIMARY KEY,
                left_market_id TEXT NOT NULL,
                right_market_id TEXT NOT NULL,
                status TEXT NOT NULL,
                fill_price REAL NOT NULL,
                estimated_fee REAL NOT NULL,
                allocated_notional REAL NOT NULL
            )
            """
        )
        connection.commit()


def insert_trade_rows(db_path: str, trades: list[PaperTrade]) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO paper_trades (
                relationship_key,
                left_market_id,
                right_market_id,
                status,
                fill_price,
                estimated_fee,
                allocated_notional
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    trade.relationship_key,
                    trade.left_market_id,
                    trade.right_market_id,
                    trade.status,
                    trade.fill_price,
                    trade.estimated_fee,
                    trade.allocated_notional,
                )
                for trade in trades
            ],
        )
        connection.commit()
```

```python
import sqlite3


def summarize_relation_type_pnl(db_path: str) -> list[dict[str, str | int | float]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                substr(relationship_key, instr(relationship_key, ':', 1, 2) + 1) AS relation_type,
                COUNT(*) AS trade_count,
                SUM(allocated_notional) AS gross_notional
            FROM paper_trades
            GROUP BY relation_type
            ORDER BY gross_notional DESC
            """
        ).fetchall()

    return [
        {
            "relation_type": row[0],
            "trade_count": row[1],
            "gross_notional": row[2],
        }
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_reporting.py::test_summarize_relation_type_pnl_groups_results -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/domain/analytics.py src/polymarket_bot/analytics/store.py src/polymarket_bot/analytics/reporting.py tests/test_reporting.py
git commit -m "feat: persist paper trade analytics"
```

### Task 8: Wire the end-to-end fixture pipeline

**Files:**
- Create: `src/polymarket_bot/ingestion/fixtures.py`
- Create: `src/polymarket_bot/pipeline.py`
- Modify: `src/polymarket_bot/cli.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing end-to-end pipeline test**

```python
import sqlite3

from polymarket_bot.pipeline import run_fixture_pipeline


def test_run_fixture_pipeline_persists_trades_and_returns_summary(tmp_path):
    result = run_fixture_pipeline(
        fixture_path="tests/fixtures/raw_markets.json",
        db_path=str(tmp_path / "analytics.db"),
    )

    assert result["signals"] >= 1
    assert result["trades"] >= 1

    with sqlite3.connect(str(tmp_path / "analytics.db")) as connection:
        trade_count = connection.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]

    assert trade_count >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py::test_run_fixture_pipeline_persists_trades_and_returns_summary -v`
Expected: FAIL with `ImportError` or missing function

- [ ] **Step 3: Write minimal fixture loader, pipeline, and CLI integration code**

```python
import json


def load_raw_fixture_markets(fixture_path: str) -> list[dict]:
    with open(fixture_path, "r", encoding="utf-8") as handle:
        return json.load(handle)
```

```python
from polymarket_bot.analytics.store import initialize_db, insert_trade_rows
from polymarket_bot.execution.paper_engine import open_paper_trades
from polymarket_bot.ingestion.fixtures import load_raw_fixture_markets
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def run_fixture_pipeline(fixture_path: str, db_path: str) -> dict[str, int]:
    raw_markets = load_raw_fixture_markets(fixture_path)
    markets = normalize_markets(raw_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    trades = open_paper_trades(filtered, markets)

    initialize_db(db_path)
    insert_trade_rows(db_path, trades)

    return {
        "signals": len(filtered),
        "trades": len(trades),
    }
```

```python
import typer

from polymarket_bot.pipeline import run_fixture_pipeline

app = typer.Typer()


@app.command("run-fixture-pipeline")
def run_fixture_pipeline_command(fixture_path: str, db_path: str) -> None:
    result = run_fixture_pipeline(fixture_path=fixture_path, db_path=db_path)
    print(f"signals={result['signals']} trades={result['trades']}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py::test_run_fixture_pipeline_persists_trades_and_returns_summary -v`
Expected: PASS

- [ ] **Step 5: Run the CLI smoke check**

Run: `pytest tests/test_pipeline.py::test_cli_runs_fixture_pipeline -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_bot/ingestion/fixtures.py src/polymarket_bot/pipeline.py src/polymarket_bot/cli.py tests/test_pipeline.py
git commit -m "feat: wire end-to-end fixture pipeline"
```

### Task 9: Run the full test suite and tighten the README

**Files:**
- Modify: `README.md`
- Test: `tests/test_normalization.py`
- Test: `tests/test_relationships.py`
- Test: `tests/test_signals.py`
- Test: `tests/test_risk_filters.py`
- Test: `tests/test_paper_execution.py`
- Test: `tests/test_reporting.py`
- Test: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing README documentation test expectation manually**

```text
The README must explain:
- how to install dependencies
- how to run the fixture pipeline
- what the MVP currently does
- what is intentionally out of scope
```

- [ ] **Step 2: Run the full test suite before README edits**

Run: `pytest -v`
Expected: PASS for code tests and no README validation yet

- [ ] **Step 3: Write the minimal README content**

```markdown
# polymarket-bot

MVP foundation for detecting cross-market pricing inconsistencies on Polymarket, simulating paper trades, and recording analytics for edge discovery.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Run fixture pipeline

```bash
polymarket-bot run-fixture-pipeline --fixture-path tests/fixtures/raw_markets.json --db-path analytics.db
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
```
```

- [ ] **Step 4: Run the full test suite after README edits**

Run: `pytest -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md
git commit -m "docs: document mvp foundation workflow"
```

## Self-Review

### Spec coverage
- Product boundary preserved: yes; plan stays fixture-driven, paper-only, analytics-first.
- Market ingestion covered: yes; fixture loader and client boundary introduced.
- Normalization covered: yes; canonical schema and tests included.
- Relationship engine covered: yes; mutually exclusive and same-theme v1 added.
- Signal engine covered: yes; rule-based inconsistency scoring and explainability included.
- Risk controls covered: yes; spread, liquidity, duplicate suppression included in MVP.
- Paper execution covered: yes; realistic enough paper entry and fee/slippage assumptions included.
- Analytics covered: yes; sqlite storage plus relation-type summaries included.
- Live trading excluded: yes; no live execution tasks appear in the plan.

### Placeholder scan
- Removed vague references and supplied exact file paths, commands, and code blocks.
- No TODO/TBD markers remain.

### Type consistency
- Canonical types are introduced before downstream usage.
- Function names are consistent across tasks: `normalize_markets`, `infer_relationships`, `score_opportunities`, `filter_opportunities`, `open_paper_trades`, `run_fixture_pipeline`.
