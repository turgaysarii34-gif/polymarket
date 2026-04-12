import json

from polymarket_bot.analytics.store import get_bankroll_state, initialize_db, insert_trade_rows, list_paper_trades, upsert_bankroll_state
from polymarket_bot.config import StrategyConfig
from polymarket_bot.domain.bankroll import BankrollState
from polymarket_bot.domain.trade import PaperTrade
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.pipeline import replay_snapshot_pipeline, run_live_snapshot_pipeline


class StubClient:
    def __init__(self, payload: list[dict]) -> None:
        self.payload = payload

    def fetch_markets(self) -> list[dict]:
        return self.payload


def test_strategy_config_defaults_hold_hours_to_twenty_four():
    config = StrategyConfig()

    assert config.paper_hold_hours == 24


def test_replay_snapshot_pipeline_persists_snapshot_run(tmp_path, live_response_payload):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 1, "markets": ' + json.dumps(live_response_payload) + '}',
        encoding="utf-8",
    )

    result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=str(tmp_path / "analytics.db"))

    assert result["market_count"] == len(live_response_payload)
    assert result["signals"] >= 0
    assert result["trades"] >= 0
    assert result["snapshot_path"] == str(snapshot_path)


def test_run_live_snapshot_pipeline_fetches_and_saves_snapshot(tmp_path, live_response_payload):
    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(live_response_payload),
        fetched_at="2026-04-06T12:00:00Z",
    )

    assert result["snapshot_path"].endswith("live.json")
    assert result["market_count"] == len(live_response_payload)


def test_run_live_snapshot_pipeline_returns_debug_summary(tmp_path, live_response_payload):
    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(live_response_payload),
        fetched_at="2026-04-07T12:00:00Z",
    )

    assert result["debug"] == {
        "normalized": len(live_response_payload),
        "relationships": 0,
        "opportunities": 0,
        "filtered": 0,
        "daily_loss_lockout": 0,
        "accepted": 0,
        "rejected_duplicate": 0,
        "rejected_stale": 0,
        "rejected_low_volume": 0,
        "rejected_high_spread": 0,
    }


def test_replay_snapshot_pipeline_returns_debug_summary(tmp_path, live_response_payload):
    snapshot_path = tmp_path / "snapshot.json"
    snapshot_path.write_text(
        '{"fetched_at": "2026-04-06T12:00:00Z", "market_count": 1, "markets": ' + json.dumps(live_response_payload) + '}',
        encoding="utf-8",
    )

    result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=str(tmp_path / "analytics.db"))

    assert result["debug"]["normalized"] == len(live_response_payload)
    assert result["debug"]["relationships"] == 0
    assert result["debug"]["opportunities"] == 0
    assert result["debug"]["filtered"] == 0
    assert result["debug"]["accepted"] == 0
    assert result["debug"]["rejected_duplicate"] == 0
    assert result["debug"]["rejected_stale"] == 0
    assert result["debug"]["rejected_low_volume"] == 0
    assert result["debug"]["rejected_high_spread"] == 0


def test_normalize_markets_adapts_live_payload_shape():
    live_market = {
        "condition_id": "cond-1",
        "question": "Will Candidate A win?",
        "end_date_iso": "2028-11-05T00:00:00Z",
        "minimum_order_size": 15,
        "rewards": {"max_spread": 240},
        "tags": ["Politics", "US"],
        "tokens": [
            {"outcome": "Yes", "price": 0.54},
            {"outcome": "No", "price": 0.46},
        ],
    }

    result = normalize_markets([live_market], fetched_at="2026-04-06T12:00:00Z")

    assert result[0].market_id == "cond-1"
    assert result[0].yes_price == 0.54
    assert result[0].no_price == 0.46
    assert result[0].category == "politics"
    assert result[0].theme_tags == ["politics", "us"]
    assert result[0].outcome_names == ["Yes", "No"]


def test_normalize_markets_handles_null_live_tags_and_tokens():
    live_market = {
        "condition_id": "cond-2",
        "question": "Will Candidate B win?",
        "end_date_iso": "2028-11-06T00:00:00Z",
        "minimum_order_size": 0,
        "rewards": None,
        "tags": None,
        "tokens": None,
    }

    result = normalize_markets([live_market], fetched_at="2026-04-06T12:00:00Z")

    assert result[0].market_id == "cond-2"
    assert result[0].category == "uncategorized"
    assert result[0].theme_tags == []
    assert result[0].outcome_names == ["Yes", "No"]


def test_pipeline_skips_open_trade_duplicates_and_only_opens_top_five(tmp_path, live_response_payload):
    first = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    assert first["trades"] <= 5

    second = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live-2.json",
        db_path=str(tmp_path / "analytics.db"),
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T13:00:00Z",
    )

    assert second["trades"] == 0
    assert second["debug"]["rejected_duplicate"] >= first["trades"]


def test_pipeline_closes_trade_after_24h_and_updates_bankroll(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                relationship_key="live-election-a:live-election-a:same_theme",
                left_market_id="live-election-a",
                right_market_id="live-election-a",
                relation_type="same_theme",
                status="open",
                fill_price=0.6,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.9,
                bankroll_at_entry=500.0,
            )
        ],
    )

    second = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live-next-day.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-09T12:30:00Z",
    )

    trades = list_paper_trades(db_path)
    state = get_bankroll_state(db_path)

    assert second["closed_trades"] >= 1
    assert any(trade["relationship_key"] == "live-election-a:live-election-a:same_theme" and trade["status"] == "closed" for trade in trades)
    assert state.current_bankroll != 500.0


def test_pipeline_does_not_close_trade_before_custom_hold_hours(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
        hold_hours=4,
    )
    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                relationship_key="hold-4h",
                left_market_id="left-market",
                right_market_id="right-market",
                relation_type="complementary",
                status="open",
                fill_price=0.6,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.9,
                bankroll_at_entry=500.0,
            )
        ],
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live-plus-3h.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T15:00:00Z",
        hold_hours=4,
    )

    trades = list_paper_trades(db_path)

    assert result["closed_trades"] == 0
    assert any(trade["relationship_key"] == "hold-4h" and trade["status"] == "open" for trade in trades)


def test_pipeline_closes_trade_after_custom_hold_hours(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
        hold_hours=1,
    )
    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                relationship_key="live-election-a:live-election-a:same_theme",
                left_market_id="live-election-a",
                right_market_id="live-election-a",
                relation_type="same_theme",
                status="open",
                fill_price=0.6,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.9,
                bankroll_at_entry=500.0,
            )
        ],
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "live-plus-1h.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T13:01:00Z",
        hold_hours=1,
    )

    trades = list_paper_trades(db_path)

    assert result["closed_trades"] >= 1
    assert any(trade["relationship_key"] == "live-election-a:live-election-a:same_theme" and trade["status"] == "closed" for trade in trades)


def test_pipeline_opens_only_remaining_global_slots(tmp_path, raw_fixture_markets):
    db_path = str(tmp_path / "analytics.db")
    initialize_db(db_path)
    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                trade_id="open-1",
                relationship_key="existing-1",
                left_market_id="left-1",
                right_market_id="right-1",
                relation_type="same_theme",
                status="open",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T11:00:00Z",
                score_at_entry=0.3,
                bankroll_at_entry=500.0,
            ),
            PaperTrade(
                trade_id="open-2",
                relationship_key="existing-2",
                left_market_id="left-2",
                right_market_id="right-2",
                relation_type="same_theme",
                status="open",
                fill_price=0.56,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T11:05:00Z",
                score_at_entry=0.31,
                bankroll_at_entry=500.0,
            ),
            PaperTrade(
                trade_id="open-3",
                relationship_key="existing-3",
                left_market_id="left-3",
                right_market_id="right-3",
                relation_type="same_theme",
                status="open",
                fill_price=0.57,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T11:10:00Z",
                score_at_entry=0.32,
                bankroll_at_entry=500.0,
            ),
        ],
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "next.json",
        db_path=db_path,
        client=StubClient(raw_fixture_markets),
        fetched_at="2026-04-08T12:30:00Z",
    )

    open_rows = [row for row in list_paper_trades(db_path) if row["status"] == "open"]

    assert result["trades"] == 2
    assert len(open_rows) == 5


def test_pipeline_opens_no_new_trades_when_already_at_global_cap(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    initialize_db(db_path)
    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                trade_id=f"open-{index}",
                relationship_key=f"existing-{index}",
                left_market_id=f"left-{index}",
                right_market_id=f"right-{index}",
                relation_type="same_theme",
                status="open",
                fill_price=0.55,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T11:00:00Z",
                score_at_entry=0.3,
                bankroll_at_entry=500.0,
            )
            for index in range(5)
        ],
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "next.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:30:00Z",
    )

    open_rows = [row for row in list_paper_trades(db_path) if row["status"] == "open"]

    assert result["trades"] == 0
    assert len(open_rows) == 5


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_closes_trade_using_current_market_based_exit_price(tmp_path, raw_fixture_markets):
    db_path = str(tmp_path / "analytics.db")
    initialize_db(db_path)
    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                trade_id="trade-1",
                relationship_key="mkt-election-2028-a:mkt-election-2028-b:same_theme",
                left_market_id="mkt-election-2028-a",
                right_market_id="mkt-election-2028-b",
                relation_type="same_theme",
                status="open",
                fill_price=0.65,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.5,
                bankroll_at_entry=500.0,
            )
        ],
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "exit.json",
        db_path=db_path,
        client=StubClient(raw_fixture_markets),
        fetched_at="2026-04-08T13:05:00Z",
        hold_hours=1,
    )

    closed_rows = [row for row in list_paper_trades(db_path) if row["status"] == "closed"]

    assert result["closed_trades"] == 1
    assert closed_rows[0]["exit_price"] != 0.5
    assert closed_rows[0]["exit_observed_total"] is not None
    assert closed_rows[0]["exit_gap"] is not None


def test_pipeline_keeps_trade_open_when_exit_market_is_missing(tmp_path):
    db_path = str(tmp_path / "analytics.db")
    initialize_db(db_path)
    insert_trade_rows(
        db_path,
        [
            PaperTrade(
                trade_id="trade-1",
                relationship_key="missing-left:missing-right:same_theme",
                left_market_id="missing-left",
                right_market_id="missing-right",
                relation_type="same_theme",
                status="open",
                fill_price=0.65,
                estimated_fee=0.2,
                allocated_notional=10.0,
                opened_at="2026-04-08T12:00:00Z",
                score_at_entry=0.5,
                bankroll_at_entry=500.0,
            )
        ],
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "exit.json",
        db_path=db_path,
        client=StubClient([]),
        fetched_at="2026-04-08T13:05:00Z",
        hold_hours=1,
    )

    open_rows = [row for row in list_paper_trades(db_path) if row["status"] == "open"]

    assert result["closed_trades"] == 0
    assert len(open_rows) == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1


def test_pipeline_stops_opening_new_trades_after_daily_five_percent_loss(tmp_path, live_response_payload):
    db_path = str(tmp_path / "analytics.db")
    run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "seed.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T12:00:00Z",
    )

    upsert_bankroll_state(
        db_path,
        BankrollState(
            current_bankroll=475.0,
            day_start_bankroll=500.0,
            last_reset_day="2026-04-08",
            daily_realized_pnl=-25.0,
        ),
    )

    result = run_live_snapshot_pipeline(
        snapshot_path=tmp_path / "locked.json",
        db_path=db_path,
        client=StubClient(live_response_payload),
        fetched_at="2026-04-08T14:00:00Z",
    )

    assert result["trades"] == 0
    assert result["debug"]["daily_loss_lockout"] == 1
