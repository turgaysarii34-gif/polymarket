from pydantic import BaseModel


class BankrollState(BaseModel):
    current_bankroll: float
    day_start_bankroll: float
    last_reset_day: str
    daily_realized_pnl: float
