from pydantic import BaseModel


class MarketRelationship(BaseModel):
    left_market_id: str
    right_market_id: str
    relation_type: str
    confidence: float
    why_linked: str
    semantic_risk_score: float
    evidence: dict[str, str | int | list[str]] = {}
