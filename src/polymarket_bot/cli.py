from pathlib import Path

import typer

from polymarket_bot.analytics.reporting import summarize_bankroll_state, summarize_closed_trade_performance
from polymarket_bot.config import StrategyConfig
from polymarket_bot.ingestion.polymarket_client import PolymarketClient
from polymarket_bot.pipeline import replay_snapshot_pipeline, run_fixture_pipeline, run_live_snapshot_pipeline

app = typer.Typer(no_args_is_help=True)


def _format_debug_summary(debug: dict[str, int]) -> str:
    return (
        f" normalized={debug['normalized']}"
        f" relationships={debug['relationships']}"
        f" opportunities={debug['opportunities']}"
        f" filtered={debug['filtered']}"
        f" accepted={debug['accepted']}"
        f" rejected_duplicate={debug['rejected_duplicate']}"
        f" rejected_stale={debug['rejected_stale']}"
        f" rejected_low_volume={debug['rejected_low_volume']}"
        f" rejected_high_spread={debug['rejected_high_spread']}"
    )


VALID_RELATION_TYPES = {"mutually_exclusive", "same_theme"}


def _format_performance_summary(db_path: str, hold_hours: int, relation_types: list[str]) -> str:
    bankroll = summarize_bankroll_state(db_path)
    performance = summarize_closed_trade_performance(db_path)
    relation_type_label = ",".join(relation_types)
    return (
        f"hold_hours={hold_hours}"
        f" relation_types={relation_type_label}"
        f" current_bankroll={bankroll['current_bankroll']}"
        f" starting_bankroll={bankroll['starting_bankroll']}"
        f" max_drawdown={bankroll['max_drawdown']}"
        f" closed_trades={performance['closed_trades']}"
        f" win_count={performance['win_count']}"
        f" loss_count={performance['loss_count']}"
        f" win_rate={performance['win_rate']}"
        f" total_realized_pnl={performance['total_realized_pnl']}"
        f" average_realized_pnl={performance['average_realized_pnl']}"
    )


def _resolve_relation_types(config: StrategyConfig, relation_type: str | None) -> list[str]:
    if relation_type is None:
        return config.paper_relation_types
    if relation_type not in VALID_RELATION_TYPES:
        raise typer.BadParameter("unknown relation type")
    return [relation_type]


def _resolve_hold_hours(config: StrategyConfig, hold_hours: int | None) -> int:
    active_hold_hours = hold_hours if hold_hours is not None else config.paper_hold_hours
    if active_hold_hours <= 0:
        raise typer.BadParameter("hold hours must be positive")
    return active_hold_hours


@app.callback()
def main() -> None:
    pass


@app.command("run-fixture-pipeline")
def run_fixture_pipeline_command(
    fixture_path: str = typer.Option(..., "--fixture-path"),
    db_path: str = typer.Option(..., "--db-path"),
) -> None:
    result = run_fixture_pipeline(fixture_path=fixture_path, db_path=db_path)
    print(f"signals={result['signals']} trades={result['trades']}")


@app.command("replay-snapshot-pipeline")
def replay_snapshot_pipeline_command(
    snapshot_path: Path = typer.Option(..., "--snapshot-path"),
    db_path: str = typer.Option(..., "--db-path"),
    hold_hours: int | None = typer.Option(None, "--hold-hours"),
    relation_type: str | None = typer.Option(None, "--relation-type"),
) -> None:
    config = StrategyConfig()
    active_hold_hours = _resolve_hold_hours(config, hold_hours)
    active_relation_types = _resolve_relation_types(config, relation_type)
    result = replay_snapshot_pipeline(
        snapshot_path=snapshot_path,
        db_path=db_path,
        hold_hours=active_hold_hours,
        relation_types=active_relation_types,
    )
    print(
        f"snapshot_path={result['snapshot_path']} market_count={result['market_count']} signals={result['signals']} trades={result['trades']} closed_trades={result['closed_trades']}"
        f"{_format_debug_summary(result['debug'])}"
    )
    print(_format_performance_summary(db_path, active_hold_hours, active_relation_types))


@app.command("fetch-live-snapshot-pipeline")
def fetch_live_snapshot_pipeline_command(
    snapshot_path: Path = typer.Option(..., "--snapshot-path"),
    db_path: str = typer.Option(..., "--db-path"),
    fetched_at: str = typer.Option(..., "--fetched-at"),
    hold_hours: int | None = typer.Option(None, "--hold-hours"),
    relation_type: str | None = typer.Option(None, "--relation-type"),
) -> None:
    config = StrategyConfig()
    active_hold_hours = _resolve_hold_hours(config, hold_hours)
    active_relation_types = _resolve_relation_types(config, relation_type)
    client = PolymarketClient(base_url=config.base_url)
    result = run_live_snapshot_pipeline(
        snapshot_path=snapshot_path,
        db_path=db_path,
        client=client,
        fetched_at=fetched_at,
        hold_hours=active_hold_hours,
        relation_types=active_relation_types,
    )
    print(
        f"snapshot_path={result['snapshot_path']} market_count={result['market_count']} signals={result['signals']} trades={result['trades']} closed_trades={result['closed_trades']}"
        f"{_format_debug_summary(result['debug'])}"
    )
    print(_format_performance_summary(db_path, active_hold_hours, active_relation_types))


if __name__ == "__main__":
    app()
