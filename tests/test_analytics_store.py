from polymarket_bot.analytics.store import initialize_db, insert_snapshot_run, list_snapshot_runs


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
