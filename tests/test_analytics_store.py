from polymarket_bot.analytics.store import (
    get_bankroll_state,
    initialize_db,
    insert_snapshot_run,
    insert_trade_rows,
    list_paper_trades,
    list_snapshot_runs,
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

    assert rows == [
        {
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
    ]


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
