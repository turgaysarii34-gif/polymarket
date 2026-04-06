from polymarket_bot.domain.market import NormalizedMarket
from polymarket_bot.domain.signal import SignalOpportunity
from polymarket_bot.domain.trade import PaperTrade


DEFAULT_NOTIONAL = 100.0
FEE_RATE = 0.02
SLIPPAGE_BUFFER = 0.01


def open_paper_trades(opportunities: list[SignalOpportunity], markets: list[NormalizedMarket]) -> list[PaperTrade]:
    market_by_id = {market.market_id: market for market in markets}
    trades: list[PaperTrade] = []

    for opportunity in opportunities:
        left = market_by_id[opportunity.left_market_id]
        right = market_by_id[opportunity.right_market_id]
        fill_price = ((left.yes_price + right.yes_price) / 2) + SLIPPAGE_BUFFER
        fee = DEFAULT_NOTIONAL * FEE_RATE

        trades.append(
            PaperTrade(
                relationship_key=opportunity.relationship_key,
                left_market_id=opportunity.left_market_id,
                right_market_id=opportunity.right_market_id,
                status="open",
                fill_price=round(fill_price, 6),
                estimated_fee=round(fee, 6),
                allocated_notional=DEFAULT_NOTIONAL,
            )
        )

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
