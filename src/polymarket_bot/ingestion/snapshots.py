import json
from pathlib import Path

from polymarket_bot.domain.snapshot import SnapshotFile


def save_snapshot_file(snapshot_path: Path, markets: list[dict], fetched_at: str) -> SnapshotFile:
    payload = {
        "fetched_at": fetched_at,
        "market_count": len(markets),
        "markets": markets,
    }
    snapshot_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return SnapshotFile(path=str(snapshot_path), fetched_at=fetched_at, market_count=len(markets))


def load_snapshot_file(snapshot_path: Path) -> dict:
    return json.loads(snapshot_path.read_text(encoding="utf-8"))
