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
