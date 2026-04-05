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
