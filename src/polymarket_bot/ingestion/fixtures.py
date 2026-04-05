import json


def load_raw_fixture_markets(fixture_path: str) -> list[dict]:
    with open(fixture_path, "r", encoding="utf-8") as handle:
        return json.load(handle)
