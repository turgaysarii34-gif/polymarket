import json

from polymarket_bot.pipeline import replay_snapshot_pipeline, run_live_snapshot_pipeline


class StubClient:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload

    def fetch_markets(self) -> list[dict]:
        return self.payload


def test_replay_snapshot_pipeline_persists_snapshot_run(tmp_path, live_response_payload):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 1, "markets": ' + json.dumps(live_response_payload) + '}',
        encoding="utf-8",
    )

    result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=str(tmp_path / "analytics.db"))

    assert result["market_count"] == len(live_response_payload)
    assert result["signals"] >= 0
    assert result["trades"] >= 0
    assert result["snapshot_path"] == str(snapshot_path)


def test_run_live_snapshot_pipeline_fetches_and_saves_snapshot(tmp_path, live_response_payload):
    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(live_response_payload),
        fetched_at="2026-04-06T12:00:00Z",
    )

    assert result["snapshot_path"].endswith("live.json")
    assert result["market_count"] == len(live_response_payload)
