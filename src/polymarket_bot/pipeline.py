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
