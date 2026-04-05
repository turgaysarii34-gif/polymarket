import typer

from polymarket_bot.pipeline import run_fixture_pipeline

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
