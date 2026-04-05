from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.relationship import MarketRelationship


MUTUALLY_EXCLUSIVE_PREFIX = "Will Candidate"


def infer_relationships(markets: list[NormalizedMarket]) -> list[MarketRelationship]:
    relationships: list[MarketRelationship] = []

    for index, left in enumerate(markets):
        for right in markets[index + 1 :]:
            if left.category == right.category and set(left.theme_tags) == set(right.theme_tags):
                relationships.append(
                    MarketRelationship(
                        left_market_id=left.market_id,
                        right_market_id=right.market_id,
                        relation_type="same_theme",
                        confidence=0.65,
                        why_linked="matching category and identical theme tags",
                        semantic_risk_score=0.35,
                    )
                )

            if left.question.startswith(MUTUALLY_EXCLUSIVE_PREFIX) and right.question.startswith(MUTUALLY_EXCLUSIVE_PREFIX):
                relationships.append(
                    MarketRelationship(
                        left_market_id=left.market_id,
                        right_market_id=right.market_id,
                        relation_type="mutually_exclusive",
                        confidence=0.9,
                        why_linked="candidate winner markets cannot both resolve yes",
                        semantic_risk_score=0.15,
                    )
                )

    return relationships
