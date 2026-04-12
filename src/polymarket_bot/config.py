from pydantic import BaseModel


class StrategyConfig(BaseModel):
    base_url: str = "https://clob.polymarket.com"
    markets_path: str = "/markets"
    request_timeout_seconds: int = 30
    min_volume: float = 50000
    max_spread_bps: int = 800
    max_snapshot_age_seconds: int = 900
    max_positions: int = 5
    paper_hold_hours: int = 24
    paper_relation_types: list[str] = ["mutually_exclusive"]
