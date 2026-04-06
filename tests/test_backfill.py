from polymarket_bot.pipeline import run_snapshot_backfill


def test_run_snapshot_backfill_replays_all_snapshot_files(tmp_path, live_response_payload):
    snapshots_dir = tmp_path / "snapshots"
    snapshots_dir.mkdir()
    for name in ("a.json", "b.json"):
        (snapshots_dir / name).write_text(
            '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 1, "markets": ' + __import__("json").dumps(live_response_payload) + '}',
            encoding="utf-8",
        )

    result = run_snapshot_backfill(snapshots_dir=snapshots_dir, db_path=str(tmp_path / "analytics.db"))

    assert result == {
        "snapshot_count": 2,
        "total_markets": 2,
        "total_signals": 0,
        "total_trades": 0,
    }
