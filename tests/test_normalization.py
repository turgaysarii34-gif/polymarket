from polymarket_bot.normalization.normalize import normalize_markets


def test_normalize_markets_produces_canonical_records(raw_fixture_markets):
    normalized = normalize_markets(raw_fixture_markets)

    assert len(normalized) == 3
    assert normalized[0].market_id == "mkt-election-2028-a"
    assert normalized[0].yes_price == 0.61
    assert normalized[0].spread_bps == 300
    assert normalized[0].category == "politics"
