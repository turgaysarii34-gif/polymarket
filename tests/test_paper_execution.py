from polymarket_bot.execution.paper_engine import close_paper_trades, open_paper_trades
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def test_close_paper_trades_marks_positions_closed_with_realized_pnl(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    trades = open_paper_trades(filtered[:1], markets)

    closed = close_paper_trades(trades, exit_price=0.72)

    assert closed[0].status == "closed"
    assert closed[0].realized_pnl > 0
    assert closed[0].exit_price == 0.72


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
