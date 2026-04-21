from polymarket_bot.domain.market import NormalizedMarket


def _adapt_live_market(raw: dict, fetched_at: str) -> dict:
    tokens = raw.get("tokens") or []
    yes_price = float(tokens[0].get("price", 0.5)) if len(tokens) >= 1 else 0.5
    no_price = float(tokens[1].get("price", max(0.0, 1 - yes_price))) if len(tokens) >= 2 else max(0.0, 1 - yes_price)
    outcomes = [token.get("outcome", "") for token in tokens] or ["Yes", "No"]
    tags = raw.get("tags") or []
    category = str(tags[0]).lower() if tags else "uncategorized"

    rewards = raw.get("rewards") or {}

    return {
        "id": raw.get("condition_id") or raw.get("id") or raw.get("question_id") or raw["question"],
        "question": raw["question"],
        "prices": {"yes": yes_price, "no": no_price},
        "volume": float(raw.get("minimum_order_size", 0)),
        "volume_is_estimated": True,
        "spread_bps": int(rewards.get("max_spread", 0) or 0),
        "close_time": raw.get("end_date_iso") or raw.get("game_start_time") or fetched_at,
        "category": category,
        "theme_tags": [str(tag).lower() for tag in tags],
        "outcomes": outcomes,
    }


def normalize_markets(raw_markets: list[dict], fetched_at: str = "fixture") -> list[NormalizedMarket]:
    normalized: list[NormalizedMarket] = []

    for raw in raw_markets:
        source = raw if "id" in raw and "prices" in raw else _adapt_live_market(raw, fetched_at)
        normalized.append(
            NormalizedMarket(
                market_id=source["id"],
                question=source["question"],
                yes_price=source["prices"]["yes"],
                no_price=source["prices"]["no"],
                volume=source["volume"],
                volume_is_estimated=source.get("volume_is_estimated", False),
                spread_bps=source["spread_bps"],
                close_time=source["close_time"],
                category=source["category"],
                theme_tags=source["theme_tags"],
                outcome_names=source["outcomes"],
                snapshot_fetched_at=fetched_at,
            )
        )

    return normalized
