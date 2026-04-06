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


def test_filter_opportunities_removes_high_spread_duplicates(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    markets[2].spread_bps = 1200
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)

    filtered = filter_opportunities(opportunities, markets, seen_keys={opportunities[0].relationship_key})

    assert all(item.relationship_key != opportunities[0].relationship_key for item in filtered)
    assert all(item.right_market_id != "mkt-election-2028-c" for item in filtered)
