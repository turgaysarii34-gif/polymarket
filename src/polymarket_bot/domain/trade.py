from pydantic import BaseModel


class PaperTrade(BaseModel):
    relationship_key: str
    left_market_id: str
    right_market_id: str
    status: str
    fill_price: float
    estimated_fee: float
    allocated_notional: float
