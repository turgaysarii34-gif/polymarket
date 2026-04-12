from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships


def test_infer_relationships_returns_hard_constraint_and_theme_links(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)

    relationships = infer_relationships(markets)

    relation_types = {(item.left_market_id, item.right_market_id, item.relation_type) for item in relationships}
    assert ("mkt-election-2028-a", "mkt-election-2028-b", "mutually_exclusive") in relation_types
    assert ("mkt-election-2028-a", "mkt-election-2028-c", "same_theme") in relation_types


def test_infer_relationships_uses_overlapping_theme_tags_and_evidence():
    markets = normalize_markets(
        [
            {
                "id": "m1",
                "question": "Will Candidate A win the 2028 election?",
                "prices": {"yes": 0.55, "no": 0.45},
                "volume": 100000.0,
                "spread_bps": 200,
                "close_time": "2028-11-05T00:00:00Z",
                "category": "politics",
                "theme_tags": ["elections", "us", "president"],
                "outcomes": ["Yes", "No"],
            },
            {
                "id": "m2",
                "question": "Will a Democrat win the 2028 election?",
                "prices": {"yes": 0.58, "no": 0.42},
                "volume": 110000.0,
                "spread_bps": 210,
                "close_time": "2028-11-05T00:00:00Z",
                "category": "politics",
                "theme_tags": ["elections", "us", "party"],
                "outcomes": ["Yes", "No"],
            },
        ],
        fetched_at="2026-04-06T12:00:00Z",
    )

    relationships = infer_relationships(markets)

    same_theme = [item for item in relationships if item.relation_type == "same_theme"]
    assert len(same_theme) == 1
    assert same_theme[0].confidence > 0.65
    assert same_theme[0].evidence == {
        "shared_category": "politics",
        "shared_tags": ["elections", "us"],
        "shared_tag_count": 2,
    }


def test_infer_relationships_links_candidate_and_independent_winner_markets(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)

    relationships = infer_relationships(markets)

    relation_types = {(item.left_market_id, item.right_market_id, item.relation_type) for item in relationships}
    assert ("mkt-election-2028-a", "mkt-election-2028-c", "mutually_exclusive") in relation_types


def test_infer_relationships_does_not_link_unrelated_win_questions_as_mutually_exclusive():
    markets = normalize_markets(
        [
            {
                "id": "m1",
                "question": "Will Candidate A win the 2028 election?",
                "prices": {"yes": 0.55, "no": 0.45},
                "volume": 100000.0,
                "spread_bps": 200,
                "close_time": "2028-11-05T00:00:00Z",
                "category": "politics",
                "theme_tags": ["elections", "us"],
                "outcomes": ["Yes", "No"],
            },
            {
                "id": "m2",
                "question": "Will Team A win the championship?",
                "prices": {"yes": 0.58, "no": 0.42},
                "volume": 110000.0,
                "spread_bps": 210,
                "close_time": "2028-11-05T00:00:00Z",
                "category": "sports",
                "theme_tags": ["sports", "championship"],
                "outcomes": ["Yes", "No"],
            },
        ],
        fetched_at="2026-04-06T12:00:00Z",
    )

    relationships = infer_relationships(markets)

    relation_types = {(item.left_market_id, item.right_market_id, item.relation_type) for item in relationships}
    assert ("m1", "m2", "mutually_exclusive") not in relation_types
