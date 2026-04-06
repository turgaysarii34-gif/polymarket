from polymarket_bot.ingestion.snapshots import load_snapshot_file, save_snapshot_file


def test_save_snapshot_file_writes_replayable_payload(tmp_path, live_response_payload):
    snapshot_path = tmp_path / "snapshot.json"

    saved = save_snapshot_file(snapshot_path=snapshot_path, markets=live_response_payload, fetched_at="2026-04-06T12:00:00Z")
    loaded = load_snapshot_file(snapshot_path)

    assert saved.path == str(snapshot_path)
    assert loaded["fetched_at"] == "2026-04-06T12:00:00Z"
    assert loaded["markets"] == live_response_payload
