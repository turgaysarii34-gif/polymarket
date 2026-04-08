import sqlite3

from polymarket_bot.analytics.store import get_bankroll_state


def summarize_relation_type_pnl(db_path: str) -> list[dict[str, str | int | float]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT relationship_key, allocated_notional
            FROM paper_trades
            ORDER BY allocated_notional DESC
            """
        ).fetchall()

    grouped: dict[str, dict[str, str | int | float]] = {}
    for relationship_key, allocated_notional in rows:
        relation_type = relationship_key.split(":")[-1]
        if relation_type not in grouped:
            grouped[relation_type] = {
                "relation_type": relation_type,
                "trade_count": 0,
                "gross_notional": 0.0,
            }
        grouped[relation_type]["trade_count"] += 1
        grouped[relation_type]["gross_notional"] += allocated_notional

    return list(grouped.values())


def summarize_category_counts(db_path: str) -> list[dict[str, str | int]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT snapshot_path, signal_count, trade_count
            FROM snapshot_runs
            ORDER BY snapshot_path ASC
            """
        ).fetchall()

    grouped: dict[str, dict[str, str | int]] = {}
    for snapshot_path, signal_count, trade_count in rows:
        category = snapshot_path.split("/")[0]
        if category not in grouped:
            grouped[category] = {
                "category": category,
                "run_count": 0,
                "signal_count": 0,
                "trade_count": 0,
            }
        grouped[category]["run_count"] += 1
        grouped[category]["signal_count"] += signal_count
        grouped[category]["trade_count"] += trade_count

    return list(grouped.values())


def summarize_theme_counts(db_path: str) -> list[dict[str, str | int]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT snapshot_path, signal_count, trade_count
            FROM snapshot_runs
            ORDER BY snapshot_path ASC
            """
        ).fetchall()

    grouped: dict[str, dict[str, str | int]] = {}
    for snapshot_path, signal_count, trade_count in rows:
        parts = snapshot_path.split("/")
        theme = parts[1] if len(parts) > 1 else "unknown"
        if theme not in grouped:
            grouped[theme] = {
                "theme": theme,
                "run_count": 0,
                "signal_count": 0,
                "trade_count": 0,
            }
        grouped[theme]["run_count"] += 1
        grouped[theme]["signal_count"] += signal_count
        grouped[theme]["trade_count"] += trade_count

    return list(grouped.values())


def summarize_closed_trade_performance(db_path: str) -> dict[str, float | int]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT realized_pnl
            FROM paper_trades
            WHERE status = 'closed'
            ORDER BY closed_at ASC, relationship_key ASC
            """
        ).fetchall()

    pnls = [float(row[0]) for row in rows]
    closed_trades = len(pnls)
    win_count = sum(1 for pnl in pnls if pnl > 0)
    loss_count = sum(1 for pnl in pnls if pnl <= 0)
    total_realized_pnl = round(sum(pnls), 6)

    return {
        "closed_trades": closed_trades,
        "win_count": win_count,
        "loss_count": loss_count,
        "win_rate": round((win_count / closed_trades) * 100, 6) if closed_trades else 0.0,
        "total_realized_pnl": total_realized_pnl,
        "average_realized_pnl": round(total_realized_pnl / closed_trades, 6) if closed_trades else 0.0,
    }


def summarize_bankroll_state(db_path: str) -> dict[str, float]:
    state = get_bankroll_state(db_path)

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT bankroll_at_entry, realized_pnl
            FROM paper_trades
            WHERE status = 'closed'
            ORDER BY closed_at ASC, relationship_key ASC
            """
        ).fetchall()

    curve: list[float] = []
    for bankroll_at_entry, realized_pnl in rows:
        curve.append(round(float(bankroll_at_entry) + float(realized_pnl), 6))

    peak = state.day_start_bankroll
    max_drawdown = 0.0
    for value in curve:
        peak = max(peak, value)
        max_drawdown = max(max_drawdown, round(peak - value, 6))

    return {
        "current_bankroll": state.current_bankroll,
        "starting_bankroll": state.day_start_bankroll,
        "max_drawdown": max_drawdown,
    }
