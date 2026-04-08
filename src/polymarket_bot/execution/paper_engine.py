from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity
from polymarket_bot.domain.trade import PaperTrade


DEFAULT_NOTIONAL = 100.0
DEFAULT_BANKROLL_RISK_PER_TRADE = 0.02
FEE_RATE = 0.02
SLIPPAGE_BUFFER = 0.01


def open_paper_trades(
    opportunities: list[SignalOpportunity],
    markets: list[NormalizedMarket],
    bankroll: float | None = None,
    max_trades: int | None = None,
    max_run_allocation: float | None = None,
    opened_at: str = "",
) -> list[PaperTrade]:
    market_by_id = {market.market_id: market for market in markets}
    trades: list[PaperTrade] = []

    if bankroll is None or max_trades is None or max_run_allocation is None:
        selected = opportunities
        per_trade_notional = DEFAULT_NOTIONAL
        run_budget = None
        relation_type = ""
        score_at_entry = 0.0
        bankroll_at_entry = 0.0
        opened_at_value = ""
    else:
        if bankroll <= 0 or max_trades <= 0 or max_run_allocation <= 0:
            return []
        per_trade_notional = round(bankroll * DEFAULT_BANKROLL_RISK_PER_TRADE, 6)
        run_budget = round(bankroll * max_run_allocation, 6)
        if per_trade_notional <= 0 or run_budget <= 0:
            return []
        selected = sorted(opportunities, key=lambda item: item.score, reverse=True)[:max_trades]
        relation_type = None
        score_at_entry = None
        bankroll_at_entry = bankroll
        opened_at_value = opened_at

    deployed = 0.0

    for opportunity in selected:
        if run_budget is not None and deployed + per_trade_notional > run_budget:
            break
        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]
        fill_price = ((left.yes_price + right.yes_price) / 2) + SLIPPAGE_BUFFER
        fee = round(per_trade_notional * FEE_RATE, 6)

        trades.append(
            PaperTrade(
                relationship_key=opportunity.relationship_key,
                left_market_id=opportunity.left_market_id,
                right_market_id=opportunity.right_market_id,
                relation_type=opportunity.relation_type if relation_type is None else relation_type,
                status="open",
                fill_price=round(fill_price, 6),
                estimated_fee=fee,
                allocated_notional=per_trade_notional,
                opened_at=opened_at_value,
                score_at_entry=opportunity.score if score_at_entry is None else score_at_entry,
                bankroll_at_entry=bankroll_at_entry,
            )
        )
        deployed = round(deployed + per_trade_notional, 6)

    return trades


def close_paper_trades(trades: list[PaperTrade], exit_price: float) -> list[PaperTrade]:
    closed: list[PaperTrade] = []

    for trade in trades:
        gross_move = (exit_price - trade.fill_price) * trade.allocated_notional
        realized_pnl = gross_move - trade.estimated_fee
        closed.append(
            trade.model_copy(
                update={
                    "status": "closed",
                    "exit_price": exit_price,
                    "realized_pnl": round(realized_pnl, 6),
                }
            )
        )

    return closed
