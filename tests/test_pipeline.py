import sqlite3
import subprocess

from typer.testing import CliRunner

import polymarket_bot.cli as cli_module
from polymarket_bot.cli import app
from polymarket_bot.pipeline import run_fixture_pipeline


class StubClient:
    def fetch_markets(self) -> list[dict]:
        return []


def test_run_fixture_pipeline_persists_trades_and_returns_summary(tmp_path):
    result = run_fixture_pipeline(
        fixture_path="tests/fixtures/raw_markets.json",
        db_path=str(tmp_path / "analytics.db"),
    )

    assert result["signals"] >= 1
    assert result["trades"] >= 1

    with sqlite3.connect(str(tmp_path / "analytics.db")) as connection:
        trade_count = connection.execute("SELECT COUNT(*) FROM paper_trades").fetchone()[0]

    assert trade_count >= 1


def test_cli_runs_fixture_pipeline(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "run-fixture-pipeline",
            "--fixture-path",
            "tests/fixtures/raw_markets.json",
            "--db-path",
            str(tmp_path / "analytics.db"),
        ],
    )

    assert result.exit_code == 0
    assert "signals=" in result.stdout
    assert "trades=" in result.stdout


def test_module_cli_runs_fixture_pipeline(tmp_path):
    result = subprocess.run(
        [
            "python3",
            "-m",
            "polymarket_bot.cli",
            "run-fixture-pipeline",
            "--fixture-path",
            "/root/polymarket-bot/tests/fixtures/raw_markets.json",
            "--db-path",
            str(tmp_path / "module.db"),
        ],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": "/root/polymarket-bot/src"},
        check=False,
    )

    assert result.returncode == 0
    assert "signals=" in result.stdout
    assert "trades=" in result.stdout


def test_cli_replay_snapshot_pipeline(tmp_path):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 0, "markets": []}',
        encoding="utf-8",
    )
    runner = CliRunner()

    result = runner.invoke(
        app,
        [
            "replay-snapshot-pipeline",
            "--snapshot-path",
            str(snapshot_path),
            "--db-path",
            str(tmp_path / "analytics.db"),
        ],
    )

    assert result.exit_code == 0
    assert "snapshot_path=" in result.stdout


def test_cli_fetch_live_snapshot_pipeline(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "PolymarketClient", lambda base_url: StubClient())
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
            "2026-04-06T12:00:00Z",
        ],
    )

    assert result.exit_code == 0
    assert "market_count=0" in result.stdout
