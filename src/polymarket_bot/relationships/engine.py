from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.relationship import MarketRelationship


WINNER_KEYWORDS = (" win the ", "winner")
WINNER_EXCLUSION_KEYWORDS = ("team", "championship", "match")


def _is_winner_type_question(question: str) -> bool:
    lowered = question.lower()
    if any(word in lowered for word in WINNER_EXCLUSION_KEYWORDS):
        return False
    return any(keyword in lowered for keyword in WINNER_KEYWORDS)


def _contest_suffix(question: str) -> str:
    lowered = question.lower().strip(" ?")
    marker = " win the "
    if marker in lowered:
        return lowered.split(marker, 1)[1].strip()
    return lowered


def _same_contest_family(left: NormalizedMarket, right: NormalizedMarket, shared_tags: list[str]) -> bool:
    return (
        left.category == right.category
        and len(shared_tags) >= 2
        and _contest_suffix(left.question) == _contest_suffix(right.question)
    )


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

            if _is_winner_type_question(left.question) and _is_winner_type_question(right.question) and _same_contest_family(left, right, shared_tags):
                relationships.append(
                    MarketRelationship(
                        left_market_id=left.market_id,
                        right_market_id=right.market_id,
                        relation_type="mutually_exclusive",
                        confidence=0.85,
                        why_linked="winner markets in the same contest cannot both resolve yes",
                        semantic_risk_score=0.15,
                        evidence={
                            "rule": "winner_family",
                            "shared_category": left.category,
                            "shared_tags": shared_tags,
                            "contest_suffix": _contest_suffix(left.question),
                        },
                    )
                )

    return relationships
