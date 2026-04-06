from datetime import datetime

from polymarket_bot.config import StrategyConfig
from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def filter_opportunities(
    opportunities: list[SignalOpportunity],
    markets: list[NormalizedMarket],
    seen_keys: set[str],
    config: StrategyConfig | None = None,
    now: str | None = None,
) -> list[SignalOpportunity]:
    active_config = config or StrategyConfig()
    market_by_id = {market.market_id: market for market in markets}
    filtered: list[SignalOpportunity] = []
    current_time = _parse_timestamp(now) if now else None

    for opportunity in opportunities:
        if opportunity.relationship_key in seen_keys:
            continue

        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]

        if current_time is not None:
            left_age = (current_time - _parse_timestamp(left.snapshot_fetched_at)).total_seconds()
            right_age = (current_time - _parse_timestamp(right.snapshot_fetched_at)).total_seconds()
            if left_age > active_config.max_snapshot_age_seconds or right_age > active_config.max_snapshot_age_seconds:
                continue

        if left.volume < active_config.min_volume or right.volume < active_config.min_volume:
            continue

        if left.spread_bps > active_config.max_spread_bps or right.spread_bps > active_config.max_spread_bps:
            continue

        filtered.append(opportunity)

    return filtered
