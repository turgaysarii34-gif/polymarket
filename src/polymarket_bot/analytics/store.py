import sqlite3

from polymarket_bot.domain.bankroll import BankrollState
from polymarket_bot.domain.trade import PaperTrade


DEFAULT_BANKROLL_STATE = BankrollState(
    current_bankroll=500.0,
    day_start_bankroll=500.0,
    last_reset_day="",
    daily_realized_pnl=0.0,
)


PAPER_TRADES_COLUMNS = [
    "relationship_key",
    "left_market_id",
    "right_market_id",
    "relation_type",
    "status",
    "fill_price",
    "estimated_fee",
    "allocated_notional",
    "opened_at",
    "score_at_entry",
    "bankroll_at_entry",
    "exit_price",
    "realized_pnl",
    "closed_at",
    "exit_snapshot_path",
]


def _ensure_paper_trades_schema(connection: sqlite3.Connection) -> None:
    columns = connection.execute("PRAGMA table_info(paper_trades)").fetchall()
    existing = {column[1] for column in columns}
    if not existing:
        connection.execute(
            """
            CREATE TABLE paper_trades (
                relationship_key TEXT PRIMARY KEY,
                left_market_id TEXT NOT NULL,
                right_market_id TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                status TEXT NOT NULL,
                fill_price REAL NOT NULL,
                estimated_fee REAL NOT NULL,
                allocated_notional REAL NOT NULL,
                opened_at TEXT NOT NULL,
                score_at_entry REAL NOT NULL,
                bankroll_at_entry REAL NOT NULL,
                exit_price REAL,
                realized_pnl REAL NOT NULL,
                closed_at REAL,
                exit_snapshot_path TEXT
            )
            """
        )
        return
    if existing == set(PAPER_TRADES_COLUMNS):
        return

    connection.execute("ALTER TABLE paper_trades RENAME TO paper_trades_legacy")
    connection.execute(
        """
        CREATE TABLE paper_trades (
            relationship_key TEXT PRIMARY KEY,
            left_market_id TEXT NOT NULL,
            right_market_id TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            status TEXT NOT NULL,
            fill_price REAL NOT NULL,
            estimated_fee REAL NOT NULL,
            allocated_notional REAL NOT NULL,
            opened_at TEXT NOT NULL,
            score_at_entry REAL NOT NULL,
            bankroll_at_entry REAL NOT NULL,
            exit_price REAL,
            realized_pnl REAL NOT NULL,
            closed_at REAL,
            exit_snapshot_path TEXT
        )
        """
    )
    connection.execute(
        """
        INSERT INTO paper_trades (
            relationship_key,
            left_market_id,
            right_market_id,
            relation_type,
            status,
            fill_price,
            estimated_fee,
            allocated_notional,
            opened_at,
            score_at_entry,
            bankroll_at_entry,
            exit_price,
            realized_pnl,
            closed_at,
            exit_snapshot_path
        )
        SELECT
            relationship_key,
            left_market_id,
            right_market_id,
            '',
            status,
            fill_price,
            estimated_fee,
            allocated_notional,
            '',
            0.0,
            0.0,
            NULL,
            0.0,
            NULL,
            NULL
        FROM paper_trades_legacy
        """
    )
    connection.execute("DROP TABLE paper_trades_legacy")


def initialize_db(db_path: str) -> None:
    with sqlite3.connect(db_path) as connection:
        _ensure_paper_trades_schema(connection)
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS bankroll_state (
                singleton_key INTEGER PRIMARY KEY CHECK (singleton_key = 1),
                current_bankroll REAL NOT NULL,
                day_start_bankroll REAL NOT NULL,
                last_reset_day TEXT NOT NULL,
                daily_realized_pnl REAL NOT NULL
            )
            """
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO bankroll_state (
                singleton_key,
                current_bankroll,
                day_start_bankroll,
                last_reset_day,
                daily_realized_pnl
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                1,
                DEFAULT_BANKROLL_STATE.current_bankroll,
                DEFAULT_BANKROLL_STATE.day_start_bankroll,
                DEFAULT_BANKROLL_STATE.last_reset_day,
                DEFAULT_BANKROLL_STATE.daily_realized_pnl,
            ),
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


def get_bankroll_state(db_path: str) -> BankrollState:
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            """
            SELECT current_bankroll, day_start_bankroll, last_reset_day, daily_realized_pnl
            FROM bankroll_state
            WHERE singleton_key = 1
            """
        ).fetchone()

    if row is None:
        return DEFAULT_BANKROLL_STATE

    return BankrollState(
        current_bankroll=row[0],
        day_start_bankroll=row[1],
        last_reset_day=row[2],
        daily_realized_pnl=row[3],
    )


def upsert_bankroll_state(db_path: str, state: BankrollState) -> None:
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO bankroll_state (
                singleton_key,
                current_bankroll,
                day_start_bankroll,
                last_reset_day,
                daily_realized_pnl
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (1, state.current_bankroll, state.day_start_bankroll, state.last_reset_day, state.daily_realized_pnl),
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
                relation_type,
                status,
                fill_price,
                estimated_fee,
                allocated_notional,
                opened_at,
                score_at_entry,
                bankroll_at_entry,
                exit_price,
                realized_pnl,
                closed_at,
                exit_snapshot_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    trade.relationship_key,
                    trade.left_market_id,
                    trade.right_market_id,
                    trade.relation_type,
                    trade.status,
                    trade.fill_price,
                    trade.estimated_fee,
                    trade.allocated_notional,
                    trade.opened_at,
                    trade.score_at_entry,
                    trade.bankroll_at_entry,
                    trade.exit_price,
                    trade.realized_pnl,
                    trade.closed_at,
                    trade.exit_snapshot_path,
                )
                for trade in trades
            ],
        )
        connection.commit()


def list_paper_trades(db_path: str) -> list[dict[str, str | float | None]]:
    with sqlite3.connect(db_path) as connection:
        rows = connection.execute(
            """
            SELECT
                relationship_key,
                left_market_id,
                right_market_id,
                relation_type,
                status,
                fill_price,
                estimated_fee,
                allocated_notional,
                opened_at,
                score_at_entry,
                bankroll_at_entry,
                exit_price,
                realized_pnl,
                closed_at,
                exit_snapshot_path
            FROM paper_trades
            ORDER BY relationship_key ASC
            """
        ).fetchall()

    return [
        {
            "relationship_key": row[0],
            "left_market_id": row[1],
            "right_market_id": row[2],
            "relation_type": row[3],
            "status": row[4],
            "fill_price": row[5],
            "estimated_fee": row[6],
            "allocated_notional": row[7],
            "opened_at": row[8],
            "score_at_entry": row[9],
            "bankroll_at_entry": row[10],
            "exit_price": row[11],
            "realized_pnl": row[12],
            "closed_at": row[13],
            "exit_snapshot_path": row[14],
        }
        for row in rows
    ]


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
