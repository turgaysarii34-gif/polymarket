import sqlite3

from polymarket_bot.analytics.store import (
    get_bankroll_state,
    initialize_db,
    insert_snapshot_run,
    insert_trade_rows,
    list_open_paper_trades,
    list_paper_trades,
    list_snapshot_runs,
    update_paper_trade_rows,
    upsert_bankroll_state,
)
from polymarket_bot.domain.bankroll import BankrollState
from polymarket_bot.domain.trade import PaperTrade


def test_initialize_db_persists_bankroll_state_and_extended_trade_fields(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))

    state = get_bankroll_state(str(db_path))

    assert state.current_bankroll == 500.0
    assert state.day_start_bankroll == 500.0
    assert state.daily_realized_pnl == 0.0


def test_insert_trade_rows_persists_extended_trade_fields(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    trade = PaperTrade(
        relationship_key="a:b:same_theme",
        left_market_id="a",
        right_market_id="b",
        relation_type="same_theme",
        status="open",
        fill_price=0.61,
        estimated_fee=0.2,
        allocated_notional=10.0,
        opened_at="2026-04-08T12:00:00Z",
        score_at_entry=0.12,
        bankroll_at_entry=500.0,
    )

    insert_trade_rows(str(db_path), [trade])
    rows = list_paper_trades(str(db_path))

    assert len(rows) == 1
    assert rows[0]["trade_id"]
    assert rows[0] == {
        "trade_id": rows[0]["trade_id"],
        "relationship_key": "a:b:same_theme",
        "left_market_id": "a",
        "right_market_id": "b",
        "relation_type": "same_theme",
        "status": "open",
        "fill_price": 0.61,
        "estimated_fee": 0.2,
        "allocated_notional": 10.0,
        "opened_at": "2026-04-08T12:00:00Z",
        "score_at_entry": 0.12,
        "bankroll_at_entry": 500.0,
        "exit_price": None,
        "realized_pnl": 0.0,
        "closed_at": None,
        "exit_snapshot_path": None,
    }


def test_upsert_bankroll_state_overwrites_singleton_row(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))

    upsert_bankroll_state(
        str(db_path),
        BankrollState(
            current_bankroll=525.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=25.0,
        ),
    )

    assert get_bankroll_state(str(db_path)) == BankrollState(
        current_bankroll=525.0,
        day_start_bankroll=500.0,
        last_reset_day="2026-04-08",
        daily_realized_pnl=25.0,
    )


def test_insert_snapshot_run_persists_ingestion_metadata(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))

    insert_snapshot_run(
        str(db_path),
        snapshot_path="snapshots/live.json",
        fetched_at="2026-04-06T12:00:00Z",
        market_count=42,
        signal_count=7,
        trade_count=3,
    )

    assert list_snapshot_runs(str(db_path)) == [
        {
            "snapshot_path": "snapshots/live.json",
            "fetched_at": "2026-04-06T12:00:00Z",
            "market_count": 42,
            "signal_count": 7,
            "trade_count": 3,
        }
    ]


def test_initialize_db_upgrades_legacy_paper_trades_schema(tmp_path):
    db_path = tmp_path / "analytics.db"

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            CREATE TABLE paper_trades (
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
            INSERT INTO paper_trades (
                relationship_key,
                left_market_id,
                right_market_id,
                status,
                fill_price,
                estimated_fee,
                allocated_notional
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy:key", "left", "right", "open", 0.61, 0.2, 10.0),
        )
        connection.commit()

    initialize_db(str(db_path))

    assert list_paper_trades(str(db_path)) == [
        {
            "trade_id": "legacy:key:legacy",
            "relationship_key": "legacy:key",
            "left_market_id": "left",
            "right_market_id": "right",
            "relation_type": "",
            "status": "open",
            "fill_price": 0.61,
            "estimated_fee": 0.2,
            "allocated_notional": 10.0,
            "opened_at": "",
            "score_at_entry": 0.0,
            "bankroll_at_entry": 0.0,
            "exit_price": None,
            "realized_pnl": 0.0,
            "closed_at": None,
            "exit_snapshot_path": None,
        }
    ]


def test_insert_trade_rows_preserves_multiple_closed_trades_for_same_relationship(tmp_path):
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
                fill_price=0.61,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.12,
                bankroll_at_entry=500.0,
                exit_price=0.7,
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
                fill_price=0.62,
                estimated_fee=0.2,
                allocated_notional=9.0,
                opened_at="2026-04-09T12:00:00Z",
                score_at_entry=0.15,
                bankroll_at_entry=501.0,
                exit_price=0.68,
                realized_pnl=-0.5,
                closed_at="2026-04-09T13:00:00Z",
                exit_snapshot_path="snapshots/two.json",
            ),
        ],
    )

    rows = list_paper_trades(str(db_path))

    assert [row["trade_id"] for row in rows] == ["trade-1", "trade-2"]
    assert [row["relationship_key"] for row in rows] == ["a:b:same_theme", "a:b:same_theme"]


def test_list_paper_trades_keeps_open_and_closed_rows_separate(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))

    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                trade_id="open-1",
                relationship_key="x:y:same_theme",
                left_market_id="x",
                right_market_id="y",
                relation_type="same_theme",
                status="open",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.2,
                bankroll_at_entry=500.0,
            ),
            PaperTrade(
                trade_id="closed-1",
                relationship_key="x:y:same_theme",
                left_market_id="x",
                right_market_id="y",
                relation_type="same_theme",
                status="closed",
                fill_price=0.57,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-07T12:00:00Z",
                score_at_entry=0.25,
                bankroll_at_entry=505.0,
                exit_price=0.6,
                realized_pnl=0.5,
                closed_at="2026-04-07T13:00:00Z",
                exit_snapshot_path="snapshots/closed.json",
            ),
        ],
    )

    rows = list_paper_trades(str(db_path))

    assert {row["trade_id"] for row in rows} == {"open-1", "closed-1"}
    assert sum(1 for row in rows if row["status"] == "open") == 1
    assert sum(1 for row in rows if row["status"] == "closed") == 1


def test_list_open_paper_trades_returns_only_open_rows(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                trade_id="open-1",
                relationship_key="a:b:same_theme",
                left_market_id="a",
                right_market_id="b",
                relation_type="same_theme",
                status="open",
                fill_price=0.61,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.12,
                bankroll_at_entry=500.0,
            ),
            PaperTrade(
                trade_id="closed-1",
                relationship_key="a:b:same_theme",
                left_market_id="a",
                right_market_id="b",
                relation_type="same_theme",
                status="closed",
                fill_price=0.61,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-07T12:00:00Z",
                score_at_entry=0.11,
                bankroll_at_entry=495.0,
                exit_price=0.63,
                realized_pnl=0.2,
                closed_at="2026-04-07T13:00:00Z",
                exit_snapshot_path="snapshots/closed.json",
            ),
        ],
    )

    rows = list_open_paper_trades(str(db_path))

    assert [row["trade_id"] for row in rows] == ["open-1"]


def test_update_paper_trade_rows_closes_specific_trade_instance(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                trade_id="open-1",
                relationship_key="a:b:same_theme",
                left_market_id="a",
                right_market_id="b",
                relation_type="same_theme",
                status="open",
                fill_price=0.61,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.12,
                bankroll_at_entry=500.0,
            )
        ],
    )

    update_paper_trade_rows(
        str(db_path),
        [
            PaperTrade(
                trade_id="open-1",
                relationship_key="a:b:same_theme",
                left_market_id="a",
                right_market_id="b",
                relation_type="same_theme",
                status="closed",
                fill_price=0.61,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.12,
                bankroll_at_entry=500.0,
                exit_price=0.7,
                realized_pnl=1.0,
                closed_at="2026-04-08T13:00:00Z",
                exit_snapshot_path="snapshots/exit.json",
            )
        ],
    )

    rows = list_paper_trades(str(db_path))

    assert rows[0]["trade_id"] == "open-1"
    assert rows[0]["status"] == "closed"
    assert rows[0]["realized_pnl"] == 1.0


def test_initialize_db_upgrades_legacy_paper_trades_schema(tmp_path):
    db_path = tmp_path / "analytics.db"

    with sqlite3.connect(str(db_path)) as connection:
        connection.execute(
            """
            CREATE TABLE paper_trades (
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
            INSERT INTO paper_trades (
                relationship_key,
                left_market_id,
                right_market_id,
                status,
                fill_price,
                estimated_fee,
                allocated_notional
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy:key", "left", "right", "open", 0.61, 0.2, 10.0),
        )
        connection.commit()

    initialize_db(str(db_path))

    assert list_paper_trades(str(db_path)) == [
        {
            "trade_id": "legacy:key:legacy",
            "relationship_key": "legacy:key",
            "left_market_id": "left",
            "right_market_id": "right",
            "relation_type": "",
            "status": "open",
            "fill_price": 0.61,
            "estimated_fee": 0.2,
            "allocated_notional": 10.0,
            "opened_at": "",
            "score_at_entry": 0.0,
            "bankroll_at_entry": 0.0,
            "exit_price": None,
            "realized_pnl": 0.0,
            "closed_at": None,
            "exit_snapshot_path": None,
        }
    ]
