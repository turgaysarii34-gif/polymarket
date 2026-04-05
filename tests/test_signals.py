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
