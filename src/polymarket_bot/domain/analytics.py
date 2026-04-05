from pydantic import BaseModel


class RelationTypeSummary(BaseModel):
    relation_type: str
    trade_count: int
    gross_notional: float
