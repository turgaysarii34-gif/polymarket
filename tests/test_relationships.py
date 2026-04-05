from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships


def test_infer_relationships_returns_hard_constraint_and_theme_links(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)

    relationships = infer_relationships(markets)

    relation_types = {(item.left_market_id, item.right_market_id, item.relation_type) for item in relationships}
    assert ("mkt-election-2028-a", "mkt-election-2028-b", "mutually_exclusive") in relation_types
    assert ("mkt-election-2028-a", "mkt-election-2028-c", "same_theme") in relation_types
