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
    current_time = fetched_at if fetched_at != "fixture" else None
    filtered = filter_opportunities(opportunities, markets, seen_keys=set(), now=current_time)
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
