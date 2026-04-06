from polymarket_bot.analytics.reporting import summarize_category_counts, summarize_theme_counts
from polymarket_bot.analytics.store import initialize_db, insert_snapshot_run, insert_trade_rows
from polymarket_bot.domain.trade import PaperTrade


def test_summarize_category_counts_groups_snapshot_runs(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_snapshot_run(
        str(db_path),
        snapshot_path="politics/us/snap1.json",
        fetched_at="2026-04-06T12:00:00Z",
        market_count=10,
        signal_count=4,
        trade_count=2,
    )
    insert_snapshot_run(
        str(db_path),
        snapshot_path="sports/soccer/snap2.json",
        fetched_at="2026-04-06T13:00:00Z",
        market_count=8,
        signal_count=2,
        trade_count=1,
    )

    assert summarize_category_counts(str(db_path)) == [
        {"category": "politics", "run_count": 1, "signal_count": 4, "trade_count": 2},
        {"category": "sports", "run_count": 1, "signal_count": 2, "trade_count": 1},
    ]


def test_summarize_theme_counts_groups_snapshot_runs(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_snapshot_run(
        str(db_path),
        snapshot_path="politics/us/snap1.json",
        fetched_at="2026-04-06T12:00:00Z",
        market_count=10,
        signal_count=4,
        trade_count=2,
    )
    insert_snapshot_run(
        str(db_path),
        snapshot_path="politics/us/snap2.json",
        fetched_at="2026-04-06T13:00:00Z",
        market_count=9,
        signal_count=3,
        trade_count=1,
    )

    assert summarize_theme_counts(str(db_path)) == [
        {"theme": "us", "run_count": 2, "signal_count": 7, "trade_count": 3},
    ]
