from polymarket_bot.analytics.reporting import summarize_bankroll_state, summarize_closed_trade_performance
from polymarket_bot.analytics.store import initialize_db, insert_trade_rows, upsert_bankroll_state
from polymarket_bot.domain.bankroll import BankrollState
from polymarket_bot.domain.trade import PaperTrade


def seed_closed_trades(db_path: str, wins: int, losses: int) -> None:
    initialize_db(db_path)
    trades: list[PaperTrade] = []

    for index in range(wins):
        trades.append(
            PaperTrade(
                relationship_key=f"win-{index}:same_theme",
                left_market_id=f"left-win-{index}",
                right_market_id=f"right-win-{index}",
                relation_type="same_theme",
                status="closed",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.8,
                bankroll_at_entry=500.0,
                exit_price=0.72,
                realized_pnl=1.5,
                closed_at="2026-04-09T12:00:00Z",
                exit_snapshot_path="snapshots/win.json",
            )
        )

    for index in range(losses):
        trades.append(
            PaperTrade(
                relationship_key=f"loss-{index}:same_theme",
                left_market_id=f"left-loss-{index}",
                right_market_id=f"right-loss-{index}",
                relation_type="same_theme",
                status="closed",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.8,
                bankroll_at_entry=500.0,
                exit_price=0.40,
                realized_pnl=-1.0,
                closed_at="2026-04-09T12:00:00Z",
                exit_snapshot_path="snapshots/loss.json",
            )
        )

    insert_trade_rows(db_path, trades)


def seed_bankroll_history(db_path: str, values: list[float]) -> None:
    initialize_db(db_path)
    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=values[-1],
            day_start_bankroll=values[0],
            last_reset_day="2026-04-04",
            daily_realized_pnl=round(values[-1] - values[0], 6),
        ),
    )

    trades: list[PaperTrade] = []
    for index, (start, end) in enumerate(zip(values, values[1:])):
        trades.append(
            PaperTrade(
                relationship_key=f"curve-{index}:same_theme",
                left_market_id=f"curve-left-{index}",
                right_market_id=f"curve-right-{index}",
                relation_type="same_theme",
                status="closed",
                fill_price=0.5,
                estimated_fee=0.0,
                allocated_notional=10.0,
                opened_at=f"2026-04-0{index + 1}T12:00:00Z",
                score_at_entry=0.5,
                bankroll_at_entry=start,
                exit_price=0.5,
                realized_pnl=round(end - start, 6),
                closed_at=f"2026-04-0{index + 1}T13:00:00Z",
                exit_snapshot_path=f"snapshots/curve-{index}.json",
            )
        )

    insert_trade_rows(db_path, trades)


def test_summarize_closed_trade_performance_reports_win_rate(tmp_path):
    db_path = tmp_path / "analytics.db"
    seed_closed_trades(str(db_path), wins=2, losses=1)

    summary = summarize_closed_trade_performance(str(db_path))

    assert summary["closed_trades"] == 3
    assert summary["win_count"] == 2
    assert summary["loss_count"] == 1
    assert summary["win_rate"] == 66.666667


def test_summarize_bankroll_curve_reports_drawdown(tmp_path):
    db_path = tmp_path / "analytics.db"
    seed_bankroll_history(str(db_path), [500.0, 520.0, 490.0, 510.0])

    summary = summarize_bankroll_state(str(db_path))

    assert summary["current_bankroll"] == 510.0
    assert summary["max_drawdown"] == 30.0


def test_summarize_closed_trade_performance_counts_repeated_relationship_history(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                trade_id="trade-1",
                relationship_key="a:b:same_theme",
                left_market_id="a",
                right_market_id="b",
                relation_type="same_theme",
                status="closed",
                fill_price=0.5,
                estimated_fee=0.1,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.4,
                bankroll_at_entry=500.0,
                exit_price=0.6,
                realized_pnl=1.0,
                closed_at="2026-04-08T13:00:00Z",
                exit_snapshot_path="snapshots/one.json",
            ),
            PaperTrade(
                trade_id="trade-2",
                relationship_key="a:b:same_theme",
                left_market_id="a",
                right_market_id="b",
                relation_type="same_theme",
                status="closed",
                fill_price=0.52,
                estimated_fee=0.1,
                allocated_notional=10.0,
                opened_at="2026-04-09T12:00:00Z",
                score_at_entry=0.42,
                bankroll_at_entry=501.0,
                exit_price=0.49,
                realized_pnl=-0.5,
                closed_at="2026-04-09T13:00:00Z",
                exit_snapshot_path="snapshots/two.json",
            ),
        ],
    )

    summary = summarize_closed_trade_performance(str(db_path))

    assert summary["closed_trades"] == 2
    assert summary["win_count"] == 1
    assert summary["loss_count"] == 1
    assert summary["total_realized_pnl"] == 0.5
