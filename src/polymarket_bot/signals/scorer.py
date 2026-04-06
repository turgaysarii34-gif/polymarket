from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.relationship import MarketRelationship
from polymarket_bot.domain.signal import SignalOpportunity


EXPECTED_SUM_BY_RELATION = {
    "mutually_exclusive": 1.0,
    "same_theme": 0.9,
}

RELATION_TYPE_BONUS = {
    "mutually_exclusive": 0.12,
    "same_theme": -0.02,
}


def score_opportunities(markets: list[NormalizedMarket], relationships: list[MarketRelationship]) -> list[SignalOpportunity]:
    market_by_id = {market.market_id: market for market in markets}
    opportunities: list[SignalOpportunity] = []

    for relation in relationships:
        left = market_by_id[relation.left_market_id]
        right = market_by_id[relation.right_market_id]
        observed_total = left.yes_price + right.yes_price
        expected_total = EXPECTED_SUM_BY_RELATION[relation.relation_type]
        raw_gap = observed_total - expected_total
        liquidity_penalty = (left.spread_bps + right.spread_bps) / 10000
        adjusted = raw_gap * relation.confidence - liquidity_penalty + RELATION_TYPE_BONUS[relation.relation_type]

        opportunities.append(
            SignalOpportunity(
                relationship_key=f"{relation.left_market_id}:{relation.right_market_id}:{relation.relation_type}",
                relation_type=relation.relation_type,
                score=round(adjusted, 6),
                left_market_id=relation.left_market_id,
                right_market_id=relation.right_market_id,
                explanation={
                    "observed_total": observed_total,
                    "expected_total": expected_total,
                    "raw_gap": raw_gap,
                    "liquidity_penalty": liquidity_penalty,
                    "confidence": relation.confidence,
                },
            )
        )

    return sorted(opportunities, key=lambda item: item.score, reverse=True)
