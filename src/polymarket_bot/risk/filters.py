from polymarket_bot.config import StrategyConfig
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity


def filter_opportunities(
    opportunities: list[SignalOpportunity],
    markets: list[NormalizedMarket],
    seen_keys: set[str],
    config: StrategyConfig | None = None,
) -> list[SignalOpportunity]:
    active_config = config or StrategyConfig()
    market_by_id = {market.market_id: market for market in markets}
    filtered: list[SignalOpportunity] = []

    for opportunity in opportunities:
        if opportunity.relationship_key in seen_keys:
            continue

        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]

        if left.volume < active_config.min_volume or right.volume < active_config.min_volume:
            continue

        if left.spread_bps > active_config.max_spread_bps or right.spread_bps > active_config.max_spread_bps:
            continue

        filtered.append(opportunity)

    return filtered
