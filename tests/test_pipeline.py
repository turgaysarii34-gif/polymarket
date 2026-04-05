import sqlite3

from typer.testing import CliRunner

from polymarket_bot.cli import app
from polymarket_bot.pipeline import run_fixture_pipeline


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
