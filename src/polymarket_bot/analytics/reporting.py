import sqlite3


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
