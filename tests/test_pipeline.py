import os
import sqlite3
import subprocess
import sys
from pathlib import Path

from typer.testing import CliRunner

import polymarket_bot.cli as cli_module
from polymarket_bot.analytics.store import initialize_db, insert_trade_rows, upsert_bankroll_state
from polymarket_bot.cli import app
from polymarket_bot.domain.bankroll import BankrollState
from polymarket_bot.domain.trade import PaperTrade
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
    repo_root = Path(__file__).resolve().parent.parent
    fixture_path = repo_root / "tests" / "fixtures" / "raw_markets.json"
    env = {
        **os.environ,
        "PYTHONPATH": str(repo_root / "src"),
    }

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "polymarket_bot.cli",
            "run-fixture-pipeline",
            "--fixture-path",
            str(fixture_path),
            "--db-path",
            str(tmp_path / "module.db"),
        ],
        capture_output=True,
        text=True,
        env=env,
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


def test_cli_fetch_live_snapshot_pipeline_prints_debug_summary(tmp_path, monkeypatch):
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
            "2026-04-07T12:00:00Z",
        ],
    )

    assert result.exit_code == 0
    assert "normalized=" in result.stdout
    assert "relationships=" in result.stdout
    assert "opportunities=" in result.stdout
    assert "rejected_low_volume=" in result.stdout


def test_cli_fetch_live_snapshot_pipeline_accepts_hold_hours_override(tmp_path, monkeypatch):
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
            "--hold-hours",
            "4",
        ],
    )

    assert result.exit_code == 0
    assert "hold_hours=4" in result.stdout


def test_cli_fetch_live_snapshot_pipeline_rejects_non_positive_hold_hours(tmp_path, monkeypatch):
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
            "--hold-hours",
            "0",
        ],
    )

    assert result.exit_code != 0
    assert "hold hours must be positive" in result.output.lower()


def test_cli_fetch_live_snapshot_pipeline_prints_default_hold_hours(tmp_path, monkeypatch):
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
    assert "hold_hours=24" in result.stdout


def test_cli_fetch_live_snapshot_pipeline_prints_performance_summary(tmp_path, monkeypatch):
    monkeypatch.setattr(cli_module, "PolymarketClient", lambda base_url: StubClient())
    db_path = tmp_path / "analytics.db"
    runner = CliRunner()

    initialize_db(str(db_path))
    upsert_bankroll_state(
        str(db_path),
        BankrollState(
            current_bankroll=510.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=10.0,
        ),
    )
    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                relationship_key="win-1:same_theme",
                left_market_id="left-win",
                right_market_id="right-win",
                relation_type="same_theme",
                status="closed",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.8,
                bankroll_at_entry=500.0,
                exit_price=0.72,
                realized_pnl=1.5,
                closed_at="2026-04-09T12:00:00Z",
                exit_snapshot_path="snapshots/win.json",
            ),
            PaperTrade(
                relationship_key="loss-1:same_theme",
                left_market_id="left-loss",
                right_market_id="right-loss",
                relation_type="same_theme",
                status="closed",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.8,
                bankroll_at_entry=520.0,
                exit_price=0.40,
                realized_pnl=-1.0,
                closed_at="2026-04-09T13:00:00Z",
                exit_snapshot_path="snapshots/loss.json",
            ),
        ],
    )

    result = runner.invoke(
        app,
        [
            "fetch-live-snapshot-pipeline",
            "--snapshot-path",
            str(tmp_path / "live.json"),
            "--db-path",
            str(db_path),
            "--fetched-at",
            "2026-04-10T12:00:00Z",
        ],
    )

    assert result.exit_code == 0
    assert "closed_trades=" in result.stdout
    assert "hold_hours=24" in result.stdout
    assert "current_bankroll=510.0" in result.stdout
    assert "starting_bankroll=510.0" in result.stdout
    assert "win_count=1" in result.stdout
    assert "loss_count=1" in result.stdout
    assert "win_rate=50.0" in result.stdout
    assert "total_realized_pnl=0.5" in result.stdout
