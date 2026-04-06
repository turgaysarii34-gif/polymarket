from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.relationship import MarketRelationship


MUTUALLY_EXCLUSIVE_PREFIX = "Will Candidate"


def infer_relationships(markets: list[NormalizedMarket]) -> list[MarketRelationship]:
    relationships: list[MarketRelationship] = []

    for index, left in enumerate(markets):
        for right in markets[index + 1 :]:
            shared_tags = sorted(set(left.theme_tags) & set(right.theme_tags))

            if left.category == right.category and len(shared_tags) >= 2:
                relationships.append(
                    MarketRelationship(
                        left_market_id=left.market_id,
                        right_market_id=right.market_id,
                        relation_type="same_theme",
                        confidence=min(0.95, 0.55 + (0.1 * len(shared_tags))),
                        why_linked="matching category and overlapping theme tags",
                        semantic_risk_score=max(0.1, 0.45 - (0.05 * len(shared_tags))),
                        evidence={
                            "shared_category": left.category,
                            "shared_tags": shared_tags,
                            "shared_tag_count": len(shared_tags),
                        },
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
                        evidence={
                            "rule": "candidate_prefix",
                            "shared_category": left.category,
                        },
                    )
                )

    return relationships
