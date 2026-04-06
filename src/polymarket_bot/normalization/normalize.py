from polymarket_bot.domain.market import NormalizedMarket


def normalize_markets(raw_markets: list[dict], fetched_at: str = "fixture") -> list[NormalizedMarket]:
    normalized: list[NormalizedMarket] = []

    for raw in raw_markets:
        normalized.append(
            NormalizedMarket(
                market_id=raw["id"],
                question=raw["question"],
                yes_price=raw["prices"]["yes"],
                no_price=raw["prices"]["no"],
                volume=raw["volume"],
                spread_bps=raw["spread_bps"],
                close_time=raw["close_time"],
                category=raw["category"],
                theme_tags=raw["theme_tags"],
                outcome_names=raw["outcomes"],
                snapshot_fetched_at=fetched_at,
            )
        )

    return normalized
