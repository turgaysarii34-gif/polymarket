import json

import pytest


@pytest.fixture
def raw_fixture_markets():
    with open("tests/fixtures/raw_markets.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture
def live_response_payload():
    with open("tests/fixtures/live_markets_response.json", "r", encoding="utf-8") as handle:
        return json.load(handle)
