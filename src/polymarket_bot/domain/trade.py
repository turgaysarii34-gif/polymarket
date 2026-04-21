from pydantic import BaseModel


class PaperTrade(BaseModel):
    trade_id: str = ""
    relationship_key: str
    left_market_id: str
    right_market_id: str
    relation_type: str = ""
    status: str
    fill_price: float
    estimated_fee: float
    allocated_notional: float
    opened_at: str = ""
    score_at_entry: float = 0.0
    bankroll_at_entry: float = 0.0
    exit_price: float | None = None
    realized_pnl: float = 0.0
    closed_at: str | None = None
    exit_snapshot_path: str | None = None
    exit_observed_total: float | None = None
    exit_expected_total: float | None = None
    exit_gap: float | None = None
