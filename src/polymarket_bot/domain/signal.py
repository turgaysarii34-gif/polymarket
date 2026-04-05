from pydantic import BaseModel


class SignalOpportunity(BaseModel):
    relationship_key: str
    relation_type: str
    score: float
    left_market_id: str
    right_market_id: str
    explanation: dict[str, float | str]
