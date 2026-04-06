from polymarket_bot.ingestion.polymarket_client import PolymarketClient


class StubResponse:
    def __init__(self, payload: list[dict]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        pass

    def json(self) -> list[dict]:
        return self._payload


class StubSession:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict]] = []

    def get(self, url: str, params: dict | None = None, timeout: int | None = None) -> StubResponse:
        self.calls.append((url, {"params": params, "timeout": timeout}))
        return StubResponse(self.payload)


def test_fetch_markets_uses_configured_endpoint_and_returns_payload(live_response_payload):
    session = StubSession(live_response_payload)
    client = PolymarketClient(base_url="https://example.com", session=session)

    result = client.fetch_markets()

    assert result == live_response_payload
    assert session.calls == [
        (
            "https://example.com/markets",
            {"params": {"closed": "false", "limit": 500}, "timeout": 30},
        )
    ]
