# Real Ingestion Replay Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the fixture-only MVP entrypoint with a real Polymarket snapshot ingestion path that can fetch live market data, save snapshots locally, replay saved snapshots through the existing paper-trading pipeline, and persist snapshot metadata for research use.

**Architecture:** Keep the existing scoring, risk, paper execution, and analytics layers unchanged as much as possible. Add a thin ingestion boundary with a real HTTP client, a snapshot storage module, and a pipeline entrypoint that accepts either live-fetched or saved raw snapshots and then hands the raw records to existing normalization and downstream stages.

**Tech Stack:** Python 3.12, pytest, pydantic, sqlite3, requests, typer, pathlib, json

---

## File Structure

### Create
- `src/polymarket_bot/domain/snapshot.py` — snapshot metadata model
- `src/polymarket_bot/ingestion/polymarket_client.py` — live Polymarket HTTP fetcher with injectable session
- `src/polymarket_bot/ingestion/snapshots.py` — save/load snapshot helpers
- `tests/fixtures/live_markets_response.json` — representative raw API payload fixture
- `tests/test_polymarket_client.py` — client fetch tests
- `tests/test_snapshots.py` — snapshot save/load tests

### Modify
- `src/polymarket_bot/domain/market.py` — add timestamp field needed for staleness filtering
- `src/polymarket_bot/config.py` — add base URL and freshness config
- `src/polymarket_bot/normalization/normalize.py` — normalize raw Polymarket payload fields and snapshot timestamp
- `src/polymarket_bot/risk/filters.py` — reject stale records using snapshot age
- `src/polymarket_bot/analytics/store.py` — persist snapshot runs and raw ingest counts
- `src/polymarket_bot/pipeline.py` — add live snapshot pipeline and replay pipeline helpers
- `src/polymarket_bot/cli.py` — add live fetch, save snapshot, and replay commands
- `tests/conftest.py` — shared live response fixture loader
- `tests/test_normalization.py` — cover live payload normalization
- `tests/test_risk_filters.py` — cover stale market rejection
- `tests/test_pipeline.py` — cover live snapshot replay path
- `README.md` — document new commands and workflow

---

### Task 1: Add live Polymarket client boundary

**Files:**
- Create: `src/polymarket_bot/ingestion/polymarket_client.py`
- Create: `tests/fixtures/live_markets_response.json`
- Create: `tests/test_polymarket_client.py`
- Modify: `src/polymarket_bot/config.py`

- [ ] **Step 1: Write the failing client test**

```python
import json

from polymarket_bot.ingestion.polymarket_client import PolymarketClient


class StubResponse:
    def __init__(self, payload: list[dict]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> list[dict]:
        return self._payload


class StubSession:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict | None = None, timeout: int | None = None) -> StubResponse:
        self.calls.append((url, {"params": params, "timeout": timeout}))
        return StubResponse(self.payload)


def test_fetch_markets_uses_configured_endpoint_and_returns_payload(live_response_payload):
    session = StubSession(live_response_payload)
    client = PolymarketClient(base_url="https://example.com", session=session)

    result = client.fetch_markets()

    assert result == live_response_payload
    assert session.calls == [
        (
            "https://example.com/markets",
            {"params": {"closed": "false", "limit": 500}, "timeout": 30},
        )
    ]
```

```json
[
  {
    "id": "live-election-a",
    "question": "Will Candidate A win?",
    "outcomes": ["Yes", "No"],
    "prices": {"yes": 0.54, "no": 0.46},
    "volume": 120000.0,
    "spread_bps": 240,
    "close_time": "2028-11-05T00:00:00Z",
    "category": "politics",
    "theme_tags": ["elections", "us"]
  }
]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_polymarket_client.py::test_fetch_markets_uses_configured_endpoint_and_returns_payload -v`
Expected: FAIL with `ModuleNotFoundError` for `polymarket_bot.ingestion.polymarket_client`

- [ ] **Step 3: Write minimal client and config code**

```python
from pydantic import BaseModel


class StrategyConfig(BaseModel):
    base_url: str = "https://clob.polymarket.com"
    markets_path: str = "/markets"
    request_timeout_seconds: int = 30
    min_volume: float = 50000
    max_spread_bps: int = 800
    max_snapshot_age_seconds: int = 900
    max_positions: int = 5
```

```python
import requests


class PolymarketClient:
    def __init__(self, base_url: str, session: requests.sessions.Session | object | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def fetch_markets(self) -> list[dict]:
        response = self.session.get(
            f"{self.base_url}/markets",
            params={"closed": "false", "limit": 500},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_polymarket_client.py::test_fetch_markets_uses_configured_endpoint_and_returns_payload -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/config.py src/polymarket_bot/ingestion/polymarket_client.py tests/fixtures/live_markets_response.json tests/test_polymarket_client.py
git commit -m "feat: add polymarket client"
```

### Task 2: Add snapshot save/load support

**Files:**
- Create: `src/polymarket_bot/domain/snapshot.py`
- Create: `src/polymarket_bot/ingestion/snapshots.py`
- Create: `tests/test_snapshots.py`

- [ ] **Step 1: Write the failing snapshot test**

```python
from polymarket_bot.ingestion.snapshots import load_snapshot_file, save_snapshot_file


def test_save_snapshot_file_writes_replayable_payload(tmp_path, live_response_payload):
    snapshot_path = tmp_path / "snapshot.json"

    saved = save_snapshot_file(snapshot_path=snapshot_path, markets=live_response_payload, fetched_at="2026-04-06T12:00:00Z")
    loaded = load_snapshot_file(snapshot_path)

    assert saved.path == str(snapshot_path)
    assert loaded["fetched_at"] == "2026-04-06T12:00:00Z"
    assert loaded["markets"] == live_response_payload
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_snapshots.py::test_save_snapshot_file_writes_replayable_payload -v`
Expected: FAIL with `ModuleNotFoundError` for `polymarket_bot.ingestion.snapshots`

- [ ] **Step 3: Write minimal snapshot model and storage code**

```python
from pydantic import BaseModel


class SnapshotFile(BaseModel):
    path: str
    fetched_at: str
    market_count: int
```

```python
import json
from pathlib import Path

from polymarket_bot.domain.snapshot import SnapshotFile


def save_snapshot_file(snapshot_path: Path, markets: list[dict], fetched_at: str) -> SnapshotFile:
    payload = {
        "fetched_at": fetched_at,
        "market_count": len(markets),
        "markets": markets,
    }
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return SnapshotFile(path=str(snapshot_path), fetched_at=fetched_at, market_count=len(markets))


def load_snapshot_file(snapshot_path: Path) -> dict:
    return json.loads(snapshot_path.read_text(encoding="utf-8"))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_snapshots.py::test_save_snapshot_file_writes_replayable_payload -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/domain/snapshot.py src/polymarket_bot/ingestion/snapshots.py tests/test_snapshots.py
git commit -m "feat: add snapshot storage"
```

### Task 3: Normalize live payload timestamps and stale-data filtering

**Files:**
- Modify: `src/polymarket_bot/domain/market.py`
- Modify: `src/polymarket_bot/normalization/normalize.py`
- Modify: `src/polymarket_bot/risk/filters.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_normalization.py`
- Modify: `tests/test_risk_filters.py`

- [ ] **Step 1: Write the failing normalization and stale filter tests**

```python
from polymarket_bot.normalization.normalize import normalize_markets


def test_normalize_markets_captures_snapshot_timestamp(live_response_payload):
    normalized = normalize_markets(live_response_payload, fetched_at="2026-04-06T12:00:00Z")

    assert normalized[0].snapshot_fetched_at == "2026-04-06T12:00:00Z"
```

```python
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def test_filter_opportunities_removes_stale_markets(live_response_payload):
    markets = normalize_markets(live_response_payload, fetched_at="2026-04-06T12:00:00Z")
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)

    filtered = filter_opportunities(
        opportunities,
        markets,
        seen_keys=set(),
        now="2026-04-06T12:20:00Z",
    )

    assert filtered == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src pytest tests/test_normalization.py::test_normalize_markets_captures_snapshot_timestamp tests/test_risk_filters.py::test_filter_opportunities_removes_stale_markets -v`
Expected: FAIL because `normalize_markets` lacks the new argument and market model lacks `snapshot_fetched_at`

- [ ] **Step 3: Write minimal timestamp and stale-filter code**

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
    snapshot_fetched_at: str
```

```python
from polymarket_bot.domain.market import NormalizedMarket


def normalize_markets(raw_markets: list[dict], fetched_at: str = "fixture") -> list[NormalizedMarket]:
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
                snapshot_fetched_at=fetched_at,
            )
        )

    return normalized
```

```python
from datetime import datetime

from polymarket_bot.config import StrategyConfig
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def filter_opportunities(
    opportunities: list[SignalOpportunity],
    markets: list[NormalizedMarket],
    seen_keys: set[str],
    config: StrategyConfig | None = None,
    now: str | None = None,
) -> list[SignalOpportunity]:
    active_config = config or StrategyConfig()
    market_by_id = {market.market_id: market for market in markets}
    filtered: list[SignalOpportunity] = []
    current_time = _parse_timestamp(now) if now else None

    for opportunity in opportunities:
        if opportunity.relationship_key in seen_keys:
            continue

        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]

        if current_time is not None:
            left_age = (current_time - _parse_timestamp(left.snapshot_fetched_at)).total_seconds()
            right_age = (current_time - _parse_timestamp(right.snapshot_fetched_at)).total_seconds()
            if left_age > active_config.max_snapshot_age_seconds or right_age > active_config.max_snapshot_age_seconds:
                continue

        if left.volume < active_config.min_volume or right.volume < active_config.min_volume:
            continue

        if left.spread_bps > active_config.max_spread_bps or right.spread_bps > active_config.max_spread_bps:
            continue

        filtered.append(opportunity)

    return filtered
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/test_normalization.py::test_normalize_markets_captures_snapshot_timestamp tests/test_risk_filters.py::test_filter_opportunities_removes_stale_markets -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/domain/market.py src/polymarket_bot/normalization/normalize.py src/polymarket_bot/risk/filters.py tests/conftest.py tests/test_normalization.py tests/test_risk_filters.py
git commit -m "feat: add snapshot freshness handling"
```

### Task 4: Persist snapshot run metadata in analytics DB

**Files:**
- Modify: `src/polymarket_bot/analytics/store.py`
- Create: `tests/test_analytics_store.py`

- [ ] **Step 1: Write the failing analytics metadata test**

```python
from polymarket_bot.analytics.store import initialize_db, insert_snapshot_run, list_snapshot_runs


def test_insert_snapshot_run_persists_ingestion_metadata(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))

    insert_snapshot_run(
        str(db_path),
        snapshot_path="snapshots/live.json",
        fetched_at="2026-04-06T12:00:00Z",
        market_count=42,
        signal_count=7,
        trade_count=3,
    )

    assert list_snapshot_runs(str(db_path)) == [
        {
            "snapshot_path": "snapshots/live.json",
            "fetched_at": "2026-04-06T12:00:00Z",
            "market_count": 42,
            "signal_count": 7,
            "trade_count": 3,
        }
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=src pytest tests/test_analytics_store.py::test_insert_snapshot_run_persists_ingestion_metadata -v`
Expected: FAIL because snapshot run helpers do not exist yet

- [ ] **Step 3: Write minimal analytics metadata persistence code**

```python
import sqlite3


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
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshot_runs (
                snapshot_path TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                market_count INTEGER NOT NULL,
                signal_count INTEGER NOT NULL,
                trade_count INTEGER NOT NULL
            )
            """
        )
        connection.commit()


def insert_snapshot_run(
    db_path: str,
    snapshot_path: str,
    fetched_at: str,
    market_count: int,
    signal_count: int,
    trade_count: int,
) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO snapshot_runs (
                snapshot_path,
                fetched_at,
                market_count,
                signal_count,
                trade_count
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (snapshot_path, fetched_at, market_count, signal_count, trade_count),
        )
        connection.commit()


def list_snapshot_runs(db_path: str) -> list[dict[str, str | int]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT snapshot_path, fetched_at, market_count, signal_count, trade_count
            FROM snapshot_runs
            ORDER BY fetched_at DESC
            """
        ).fetchall()

    return [
        {
            "snapshot_path": row[0],
            "fetched_at": row[1],
            "market_count": row[2],
            "signal_count": row[3],
            "trade_count": row[4],
        }
        for row in rows
    ]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=src pytest tests/test_analytics_store.py::test_insert_snapshot_run_persists_ingestion_metadata -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/analytics/store.py tests/test_analytics_store.py
git commit -m "feat: persist snapshot metadata"
```

### Task 5: Add live snapshot and replay pipeline entrypoints

**Files:**
- Modify: `src/polymarket_bot/pipeline.py`
- Create: `tests/test_pipeline_live.py`

- [ ] **Step 1: Write the failing live pipeline tests**

```python
from polymarket_bot.pipeline import replay_snapshot_pipeline


def test_replay_snapshot_pipeline_persists_snapshot_run(tmp_path, live_response_payload):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 3, "markets": ' + __import__("json").dumps(live_response_payload) + '}',
        encoding="utf-8",
    )

    result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=str(tmp_path / "analytics.db"))

    assert result["market_count"] == len(live_response_payload)
    assert result["signals"] >= 0
    assert result["trades"] >= 0
    assert result["snapshot_path"] == str(snapshot_path)
```

```python
from polymarket_bot.pipeline import run_live_snapshot_pipeline


class StubClient:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload

    def fetch_markets(self) -> list[dict]:
        return self.payload


def test_run_live_snapshot_pipeline_fetches_and_saves_snapshot(tmp_path, live_response_payload):
    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(live_response_payload),
        fetched_at="2026-04-06T12:00:00Z",
    )

    assert result["snapshot_path"].endswith("live.json")
    assert result["market_count"] == len(live_response_payload)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src pytest tests/test_pipeline_live.py::test_replay_snapshot_pipeline_persists_snapshot_run tests/test_pipeline_live.py::test_run_live_snapshot_pipeline_fetches_and_saves_snapshot -v`
Expected: FAIL because new pipeline helpers do not exist yet

- [ ] **Step 3: Write minimal live and replay pipeline code**

```python
from pathlib import Path

from polymarket_bot.analytics.store import initialize_db, insert_snapshot_run, insert_trade_rows
from polymarket_bot.execution.paper_engine import open_paper_trades
from polymarket_bot.ingestion.fixtures import load_raw_fixture_markets
from polymarket_bot.ingestion.snapshots import load_snapshot_file, save_snapshot_file
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def _run_raw_market_pipeline(raw_markets: list[dict], fetched_at: str, db_path: str, snapshot_path: str) -> dict[str, int | str]:
    markets = normalize_markets(raw_markets, fetched_at=fetched_at)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set(), now=fetched_at)
    trades = open_paper_trades(filtered, markets)

    initialize_db(db_path)
    insert_trade_rows(db_path, trades)
    insert_snapshot_run(
        db_path,
        snapshot_path=snapshot_path,
        fetched_at=fetched_at,
        market_count=len(raw_markets),
        signal_count=len(filtered),
        trade_count=len(trades),
    )

    return {
        "snapshot_path": snapshot_path,
        "market_count": len(raw_markets),
        "signals": len(filtered),
        "trades": len(trades),
    }


def run_fixture_pipeline(fixture_path: str, db_path: str) -> dict[str, int]:
    raw_markets = load_raw_fixture_markets(fixture_path)
    result = _run_raw_market_pipeline(raw_markets, fetched_at="fixture", db_path=db_path, snapshot_path=fixture_path)
    return {"signals": result["signals"], "trades": result["trades"]}


def replay_snapshot_pipeline(snapshot_path: Path, db_path: str) -> dict[str, int | str]:
    payload = load_snapshot_file(snapshot_path)
    return _run_raw_market_pipeline(payload["markets"], payload["fetched_at"], db_path=db_path, snapshot_path=str(snapshot_path))


def run_live_snapshot_pipeline(snapshot_path: Path, db_path: str, client: object, fetched_at: str) -> dict[str, int | str]:
    raw_markets = client.fetch_markets()
    save_snapshot_file(snapshot_path=snapshot_path, markets=raw_markets, fetched_at=fetched_at)
    return _run_raw_market_pipeline(raw_markets, fetched_at=fetched_at, db_path=db_path, snapshot_path=str(snapshot_path))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/test_pipeline_live.py::test_replay_snapshot_pipeline_persists_snapshot_run tests/test_pipeline_live.py::test_run_live_snapshot_pipeline_fetches_and_saves_snapshot -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/polymarket_bot/pipeline.py tests/test_pipeline_live.py
git commit -m "feat: add replayable live snapshot pipeline"
```

### Task 6: Add CLI commands for fetch-and-save and replay workflows

**Files:**
- Modify: `src/polymarket_bot/cli.py`
- Modify: `README.md`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
from typer.testing import CliRunner

from polymarket_bot.cli import app


def test_cli_replay_snapshot_pipeline(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 0, "markets": []}',
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "replay-snapshot-pipeline",
            "--snapshot-path",
            str(snapshot_path),
            "--db-path",
            str(tmp_path / "analytics.db"),
        ],
    )

    assert result.exit_code == 0
    assert "snapshot_path=" in result.stdout
```

```python
from typer.testing import CliRunner

import polymarket_bot.cli as cli_module
from polymarket_bot.cli import app


class StubClient:
    def fetch_markets(self) -> list[dict]:
        return []


def test_cli_fetch_live_snapshot_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "PolymarketClient", lambda base_url: StubClient())
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "fetch-live-snapshot-pipeline",
            "--snapshot-path",
            str(tmp_path / "live.json"),
            "--db-path",
            str(tmp_path / "analytics.db"),
            "--fetched-at",
            "2026-04-06T12:00:00Z",
        ],
    )

    assert result.exit_code == 0
    assert "market_count=0" in result.stdout
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=src pytest tests/test_pipeline.py::test_cli_replay_snapshot_pipeline tests/test_pipeline.py::test_cli_fetch_live_snapshot_pipeline -v`
Expected: FAIL because CLI commands do not exist yet

- [ ] **Step 3: Write minimal CLI and README code**

```python
import typer
from pathlib import Path

from polymarket_bot.config import StrategyConfig
from polymarket_bot.ingestion.polymarket_client import PolymarketClient
from polymarket_bot.pipeline import replay_snapshot_pipeline, run_fixture_pipeline, run_live_snapshot_pipeline

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    pass


@app.command("run-fixture-pipeline")
def run_fixture_pipeline_command(
    fixture_path: str = typer.Option(..., "--fixture-path"),
    db_path: str = typer.Option(..., "--db-path"),
) -> None:
    result = run_fixture_pipeline(fixture_path=fixture_path, db_path=db_path)
    print(f"signals={result['signals']} trades={result['trades']}")


@app.command("replay-snapshot-pipeline")
def replay_snapshot_pipeline_command(
    snapshot_path: Path = typer.Option(..., "--snapshot-path"),
    db_path: str = typer.Option(..., "--db-path"),
) -> None:
    result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=db_path)
    print(
        f"snapshot_path={result['snapshot_path']} market_count={result['market_count']} signals={result['signals']} trades={result['trades']}"
    )


@app.command("fetch-live-snapshot-pipeline")
def fetch_live_snapshot_pipeline_command(
    snapshot_path: Path = typer.Option(..., "--snapshot-path"),
    db_path: str = typer.Option(..., "--db-path"),
    fetched_at: str = typer.Option(..., "--fetched-at"),
) -> None:
    config = StrategyConfig()
    client = PolymarketClient(base_url=config.base_url)
    result = run_live_snapshot_pipeline(
        snapshot_path=snapshot_path,
        db_path=db_path,
        client=client,
        fetched_at=fetched_at,
    )
    print(
        f"snapshot_path={result['snapshot_path']} market_count={result['market_count']} signals={result['signals']} trades={result['trades']}"
    )
```

```markdown
## Replay saved snapshot

```bash
PYTHONPATH=src python -m polymarket_bot.cli replay-snapshot-pipeline --snapshot-path snapshots/live.json --db-path analytics.db
```

## Fetch live snapshot and run pipeline

```bash
PYTHONPATH=src python -m polymarket_bot.cli fetch-live-snapshot-pipeline --snapshot-path snapshots/live.json --db-path analytics.db --fetched-at 2026-04-06T12:00:00Z
```
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=src pytest tests/test_pipeline.py::test_cli_replay_snapshot_pipeline tests/test_pipeline.py::test_cli_fetch_live_snapshot_pipeline -v`
Expected: PASS

- [ ] **Step 5: Run the full suite**

Run: `PYTHONPATH=src pytest -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/polymarket_bot/cli.py README.md tests/test_pipeline.py
git commit -m "feat: add snapshot replay CLI workflows"
```

## Self-Review

### Spec coverage
- Real ingestion covered: yes; plan adds real HTTP client and live fetch command.
- Replayable research workflow covered: yes; snapshots can be saved, loaded, replayed, and logged.
- Stale data rejection covered: yes; freshness timestamp and filter changes included.
- Analytics expansion covered: yes; snapshot metadata persistence added.
- Live trading excluded: yes; no execution against live capital is introduced.

### Placeholder scan
- No TBD/TODO markers remain.
- All tasks include exact files, test commands, and implementation snippets.

### Type consistency
- New types introduced consistently: `SnapshotFile`, `snapshot_fetched_at`, `insert_snapshot_run`, `list_snapshot_runs`, `run_live_snapshot_pipeline`, `replay_snapshot_pipeline`.
