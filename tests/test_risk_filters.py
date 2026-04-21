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


def test_filter_opportunities_reports_reject_reasons(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    markets[2].spread_bps = 1200
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)

    filtered, debug = filter_opportunities(
        opportunities,
        markets,
        seen_keys={opportunities[0].relationship_key},
        include_debug=True,
    )

    assert all(item.relationship_key != opportunities[0].relationship_key for item in filtered)
    assert debug["rejected_duplicate"] == 1
    assert debug["rejected_stale"] == 0
    assert debug["rejected_low_volume"] == 0
    assert debug["rejected_high_spread"] >= 1
    assert len(filtered) == debug["accepted"]
    assert debug["accepted"] + sum(
        debug[key]
        for key in (
            "rejected_duplicate",
            "rejected_stale",
            "rejected_low_volume",
            "rejected_high_spread",
        )
    ) == len(opportunities)


def test_filter_opportunities_reports_stale_reject_reason(live_response_payload):
    markets = normalize_markets(live_response_payload, fetched_at="2026-04-06T12:00:00Z")
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)

    filtered, debug = filter_opportunities(
        opportunities,
        markets,
        seen_keys=set(),
        now="2026-04-06T12:20:00Z",
        include_debug=True,
    )

    assert filtered == []
    assert debug["accepted"] == 0
    assert debug["rejected_stale"] == len(opportunities)


def test_filter_opportunities_skips_low_volume_for_live_adapted_markets():
    live_markets = [
        {
            "condition_id": "cond-1",
            "question": "Will Candidate A win?",
            "end_date_iso": "2028-11-05T00:00:00Z",
            "minimum_order_size": 15,
            "rewards": {"max_spread": 240},
            "tags": ["Politics", "US"],
            "tokens": [
                {"outcome": "Yes", "price": 0.54},
                {"outcome": "No", "price": 0.46},
            ],
        },
        {
            "condition_id": "cond-2",
            "question": "Will Candidate B win?",
            "end_date_iso": "2028-11-05T00:00:00Z",
            "minimum_order_size": 15,
            "rewards": {"max_spread": 240},
            "tags": ["Politics", "US"],
            "tokens": [
                {"outcome": "Yes", "price": 0.41},
                {"outcome": "No", "price": 0.59},
            ],
        },
    ]
    markets = normalize_markets(live_markets, fetched_at="2026-04-06T12:00:00Z")
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)

    filtered, debug = filter_opportunities(
        opportunities,
        markets,
        seen_keys=set(),
        now="2026-04-06T12:00:00Z",
        include_debug=True,
    )

    assert len(opportunities) >= 1
    assert len(filtered) == len(opportunities)
    assert debug["accepted"] == len(opportunities)
    assert debug["rejected_low_volume"] == 0
    assert all(market.volume == 15 for market in markets)
    assert all(market.volume_is_estimated for market in markets)


def test_normalize_markets_marks_live_volume_as_estimated():
    live_markets = [
        {
            "condition_id": "cond-1",
            "question": "Will Candidate A win?",
            "end_date_iso": "2028-11-05T00:00:00Z",
            "minimum_order_size": 15,
            "rewards": {"max_spread": 240},
            "tags": ["Politics", "US"],
            "tokens": [
                {"outcome": "Yes", "price": 0.54},
                {"outcome": "No", "price": 0.46},
            ],
        }
    ]

    markets = normalize_markets(live_markets, fetched_at="2026-04-06T12:00:00Z")

    assert markets[0].volume == 15
    assert markets[0].volume_is_estimated is True
