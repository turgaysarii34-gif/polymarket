from pydantic import BaseModel


class NormalizedMarket(BaseModel):
    market_id: str
    question: str
    yes_price: float
    no_price: float
    volume: float
    spread_bps: int
    close_time: str
    category: str
    theme_tags: list[str]
    outcome_names: list[str]
