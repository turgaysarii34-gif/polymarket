import sqlite3

from polymarket_bot.domain.trade import PaperTrade


def initialize_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS paper_trades (
                relationship_key TEXT PRIMARY KEY,
                left_market_id TEXT NOT NULL,
                right_market_id TEXT NOT NULL,
                status TEXT NOT NULL,
                fill_price REAL NOT NULL,
                estimated_fee REAL NOT NULL,
                allocated_notional REAL NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS snapshot_runs (
                snapshot_path TEXT PRIMARY KEY,
                fetched_at TEXT NOT NULL,
                market_count INTEGER NOT NULL,
                signal_count INTEGER NOT NULL,
                trade_count INTEGER NOT NULL
            )
            """
        )
        connection.commit()


def insert_trade_rows(db_path: str, trades: list[PaperTrade]) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.executemany(
            """
            INSERT OR REPLACE INTO paper_trades (
                relationship_key,
                left_market_id,
                right_market_id,
                status,
                fill_price,
                estimated_fee,
                allocated_notional
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    trade.relationship_key,
                    trade.left_market_id,
                    trade.right_market_id,
                    trade.status,
                    trade.fill_price,
                    trade.estimated_fee,
                    trade.allocated_notional,
                )
                for trade in trades
            ],
        )
        connection.commit()


def insert_snapshot_run(
    db_path: str,
    snapshot_path: str,
    fetched_at: str,
    market_count: int,
    signal_count: int,
    trade_count: int,
) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO snapshot_runs (
                snapshot_path,
                fetched_at,
                market_count,
                signal_count,
                trade_count
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (snapshot_path, fetched_at, market_count, signal_count, trade_count),
        )
        connection.commit()


def list_snapshot_runs(db_path: str) -> list[dict[str, str | int]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT snapshot_path, fetched_at, market_count, signal_count, trade_count
            FROM snapshot_runs
            ORDER BY fetched_at DESC
            """
        ).fetchall()

    return [
        {
            "snapshot_path": row[0],
            "fetched_at": row[1],
            "market_count": row[2],
            "signal_count": row[3],
            "trade_count": row[4],
        }
        for row in rows
    ]
