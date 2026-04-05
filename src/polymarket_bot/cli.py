import typer

app = typer.Typer(no_args_is_help=True)


@app.callback()
def main() -> None:
    pass


@app.command("run-fixture-pipeline")
def run_fixture_pipeline(
    fixture_path: str = typer.Option(..., "--fixture-path"),
    db_path: str = typer.Option(..., "--db-path"),
) -> None:
    print(f"signals=0 trades=0 fixture={fixture_path} db={db_path}")
