from pydantic import BaseModel


class StrategyConfig(BaseModel):
    min_volume: float = 50000
    max_spread_bps: int = 800
    max_positions: int = 5
