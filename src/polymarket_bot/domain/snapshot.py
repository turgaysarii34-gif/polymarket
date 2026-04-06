from pydantic import BaseModel


class SnapshotFile(BaseModel):
    path: str
    fetched_at: str
    market_count: int
