import requests


class PolymarketClient:
    def __init__(self, base_url: str, session: requests.sessions.Session | object | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = session or requests.Session()

    def fetch_markets(self) -> list[dict]:
        response = self.session.get(
            f"{self.base_url}/markets",
            params={"closed": "false", "limit": 500},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, dict) and "data" in payload:
            return payload["data"]
        return payload
