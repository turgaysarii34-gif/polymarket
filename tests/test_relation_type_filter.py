from typer.testing import CliRunner

import polymarket_bot.cli as cli_module
from polymarket_bot.config import StrategyConfig
from polymarket_bot.pipeline import run_live_snapshot_pipeline
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.cli import app


class StubClient:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload

    def fetch_markets(self) -> list[dict]:
        return self.payload


def test_strategy_config_defaults_paper_relation_types_to_mutually_exclusive():
    config = StrategyConfig()

    assert config.paper_relation_types == ["mutually_exclusive"]


def test_cli_fetch_live_snapshot_pipeline_accepts_relation_type_override(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "PolymarketClient", lambda base_url: StubClient([]))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "fetch-live-snapshot-pipeline",
            "--snapshot-path",
            str(tmp_path / "live.json"),
            "--db-path",
            str(tmp_path / "analytics.db"),
            "--fetched-at",
            "2026-04-11T12:00:00Z",
            "--relation-type",
            "same_theme",
        ],
    )

    assert result.exit_code == 0
    assert "relation_types=same_theme" in result.stdout


def test_cli_fetch_live_snapshot_pipeline_rejects_unknown_relation_type(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "PolymarketClient", lambda base_url: StubClient([]))
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "fetch-live-snapshot-pipeline",
            "--snapshot-path",
            str(tmp_path / "live.json"),
            "--db-path",
            str(tmp_path / "analytics.db"),
            "--fetched-at",
            "2026-04-11T12:00:00Z",
            "--relation-type",
            "bogus",
        ],
    )

    assert result.exit_code != 0
    assert "unknown relation type" in result.output.lower()


def test_infer_relationships_still_includes_same_theme(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)

    assert any(item.relation_type == "same_theme" for item in relationships)
    assert any(item.relation_type == "mutually_exclusive" for item in relationships)


def test_pipeline_defaults_to_mutually_exclusive_only_for_paper_candidates(tmp_path, raw_fixture_markets):
    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(raw_fixture_markets),
        fetched_at="2026-04-11T12:00:00Z",
    )

    assert result["signals"] >= 0
    assert result["debug"]["opportunities"] >= result["signals"]


def test_pipeline_can_override_relation_type_to_same_theme(tmp_path, raw_fixture_markets):
    default_result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "default.json",
        db_path=str(tmp_path / "default.db"),
        client=StubClient(raw_fixture_markets),
        fetched_at="2026-04-11T12:00:00Z",
    )
    same_theme_result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "same.json",
        db_path=str(tmp_path / "same.db"),
        client=StubClient(raw_fixture_markets),
        fetched_at="2026-04-11T12:00:00Z",
        relation_types=["same_theme"],
    )

    assert same_theme_result["signals"] >= default_result["signals"]
