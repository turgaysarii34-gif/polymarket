import json

from polymarket_bot.normalization.normalize import normalize_markets
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


def test_normalize_markets_adapts_live_payload_shape():
    live_market = {
        "condition_id": "cond-1",
        "question": "Will Candidate A win?",
        "end_date_iso": "2028-11-05T00:00:00Z",
        "minimum_order_size": 15,
        "rewards": {"max_spread": 240},
        "tags": ["Politics", "US"],
        "tokens": [
            {"outcome": "Yes", "price": 0.54},
            {"outcome": "No", "price": 0.46},
        ],
    }

    result = normalize_markets([live_market], fetched_at="2026-04-06T12:00:00Z")

    assert result[0].market_id == "cond-1"
    assert result[0].yes_price == 0.54
    assert result[0].no_price == 0.46
    assert result[0].category == "politics"
    assert result[0].theme_tags == ["politics", "us"]
    assert result[0].outcome_names == ["Yes", "No"]
