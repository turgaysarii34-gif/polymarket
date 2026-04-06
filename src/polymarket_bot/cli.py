from pathlib import Path

import typer

from polymarket_bot.config import StrategyConfig
from polymarket_bot.ingestion.polymarket_client import PolymarketClient
from polymarket_bot.pipeline import replay_snapshot_pipeline, run_fixture_pipeline, run_live_snapshot_pipeline

app = typer.Typer(no_args_is_help=True)


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
) -> None:
    result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=db_path)
    print(
        f"snapshot_path={result['snapshot_path']} market_count={result['market_count']} signals={result['signals']} trades={result['trades']}"
    )


@app.command("fetch-live-snapshot-pipeline")
def fetch_live_snapshot_pipeline_command(
    snapshot_path: Path = typer.Option(..., "--snapshot-path"),
    db_path: str = typer.Option(..., "--db-path"),
    fetched_at: str = typer.Option(..., "--fetched-at"),
) -> None:
    config = StrategyConfig()
    client = PolymarketClient(base_url=config.base_url)
    result = run_live_snapshot_pipeline(
        snapshot_path=snapshot_path,
        db_path=db_path,
        client=client,
        fetched_at=fetched_at,
    )
    print(
        f"snapshot_path={result['snapshot_path']} market_count={result['market_count']} signals={result['signals']} trades={result['trades']}"
    )


if __name__ == "__main__":
    app()
