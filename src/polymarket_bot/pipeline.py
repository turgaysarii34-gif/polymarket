from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4

from polymarket_bot.analytics.store import (
    get_bankroll_state,
    initialize_db,
    insert_snapshot_run,
    insert_trade_rows,
    list_open_paper_trades,
    list_paper_trades,
    update_paper_trade_rows,
    upsert_bankroll_state,
)
from polymarket_bot.config import StrategyConfig
from polymarket_bot.domain.bankroll import BankrollState
from polymarket_bot.domain.trade import PaperTrade
from polymarket_bot.execution.paper_engine import close_paper_trades, open_paper_trades
from polymarket_bot.ingestion.fixtures import load_raw_fixture_markets
from polymarket_bot.ingestion.snapshots import load_snapshot_file, save_snapshot_file
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


MAX_RUN_ALLOCATION = 0.10
DAILY_LOSS_LIMIT_FRACTION = 0.05
EXPECTED_SUM_BY_RELATION = {
    "mutually_exclusive": 1.0,
    "same_theme": 0.9,
}


def _parse_timestamp(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _paper_trade_from_row(row: dict[str, str | float | None]) -> PaperTrade:
    return PaperTrade(
        trade_id=str(row["trade_id"]),
        relationship_key=str(row["relationship_key"]),
        left_market_id=str(row["left_market_id"]),
        right_market_id=str(row["right_market_id"]),
        relation_type=str(row["relation_type"]),
        status=str(row["status"]),
        fill_price=float(row["fill_price"]),
        estimated_fee=float(row["estimated_fee"]),
        allocated_notional=float(row["allocated_notional"]),
        opened_at=str(row["opened_at"]),
        score_at_entry=float(row["score_at_entry"]),
        bankroll_at_entry=float(row["bankroll_at_entry"]),
        exit_price=float(row["exit_price"]) if row["exit_price"] is not None else None,
        realized_pnl=float(row["realized_pnl"]),
        closed_at=str(row["closed_at"]) if row["closed_at"] is not None else None,
        exit_snapshot_path=str(row["exit_snapshot_path"]) if row["exit_snapshot_path"] is not None else None,
    )


def _refresh_bankroll_day(state: BankrollState, fetched_at: str) -> BankrollState:
    current_day = fetched_at[:10]
    if state.last_reset_day == current_day:
        return state
    return BankrollState(
        current_bankroll=state.current_bankroll,
        day_start_bankroll=state.current_bankroll,
        last_reset_day=current_day,
        daily_realized_pnl=0.0,
    )


def _build_market_lookup(markets: list) -> dict[str, object]:
    return {market.market_id: market for market in markets}


def _compute_market_exit(left, right, relation_type: str) -> tuple[float, float, float, float]:
    exit_observed_total = round(left.yes_price + right.yes_price, 6)
    exit_expected_total = EXPECTED_SUM_BY_RELATION[relation_type]
    exit_gap = round(exit_observed_total - exit_expected_total, 6)
    exit_price = round((left.yes_price + right.yes_price) / 2, 6)
    return exit_price, exit_observed_total, exit_expected_total, exit_gap


def _run_raw_market_pipeline(
    raw_markets: list[dict],
    fetched_at: str,
    db_path: str,
    snapshot_path: str,
    hold_hours: int,
) -> dict[str, int | str | dict[str, int]]:
    initialize_db(db_path)
    bankroll_state = _refresh_bankroll_day(get_bankroll_state(db_path), fetched_at)
    open_trade_rows = list_open_paper_trades(db_path)
    open_trades = [_paper_trade_from_row(row) for row in open_trade_rows]
    active_hold_duration = timedelta(hours=hold_hours)
    markets = normalize_markets(raw_markets, fetched_at=fetched_at)
    market_by_id = _build_market_lookup(markets)

    closed_trades: list[PaperTrade] = []
    still_open_trades: list[PaperTrade] = []
    if fetched_at != "fixture":
        current_time = _parse_timestamp(fetched_at)
        for trade in open_trades:
            if trade.opened_at and current_time - _parse_timestamp(trade.opened_at) >= active_hold_duration:
                left = market_by_id.get(trade.left_market_id)
                right = market_by_id.get(trade.right_market_id)
                if left is None or right is None:
                    still_open_trades.append(trade)
                    continue
                exit_price, exit_observed_total, exit_expected_total, exit_gap = _compute_market_exit(
                    left,
                    right,
                    trade.relation_type,
                )
                closed_trade = close_paper_trades(
                    [trade],
                    exit_price=exit_price,
                    exit_observed_total=exit_observed_total,
                    exit_expected_total=exit_expected_total,
                    exit_gap=exit_gap,
                )[0].model_copy(update={"closed_at": fetched_at, "exit_snapshot_path": snapshot_path})
                closed_trades.append(closed_trade)
            else:
                still_open_trades.append(trade)
    else:
        still_open_trades = open_trades

    if closed_trades:
        realized_pnl = round(sum(trade.realized_pnl for trade in closed_trades), 6)
        bankroll_state = BankrollState(
            current_bankroll=round(bankroll_state.current_bankroll + realized_pnl, 6),
            day_start_bankroll=bankroll_state.day_start_bankroll,
            last_reset_day=bankroll_state.last_reset_day,
            daily_realized_pnl=round(bankroll_state.daily_realized_pnl + realized_pnl, 6),
        )
        update_paper_trade_rows(db_path, closed_trades)

    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    current_time = fetched_at if fetched_at != "fixture" else None
    seen_keys = {trade.relationship_key for trade in still_open_trades}
    filtered, filter_debug = filter_opportunities(opportunities, markets, seen_keys=seen_keys, now=current_time, include_debug=True)

    config = StrategyConfig()
    daily_loss_lockout = 0
    trades: list[PaperTrade] = []
    remaining_open_count = len(still_open_trades)
    available_slots = max(config.max_positions - remaining_open_count, 0)
    if bankroll_state.day_start_bankroll > 0 and bankroll_state.daily_realized_pnl <= -(bankroll_state.day_start_bankroll * DAILY_LOSS_LIMIT_FRACTION):
        daily_loss_lockout = 1
    elif available_slots > 0:
        trades = [
            trade.model_copy(update={"trade_id": uuid4().hex})
            for trade in open_paper_trades(
                filtered,
                markets,
                bankroll=bankroll_state.current_bankroll,
                max_trades=available_slots,
                max_run_allocation=MAX_RUN_ALLOCATION,
                opened_at=fetched_at,
            )
        ]
        if trades:
            insert_trade_rows(db_path, trades)

    upsert_bankroll_state(db_path, bankroll_state)
    insert_snapshot_run(
        db_path,
        snapshot_path=snapshot_path,
        fetched_at=fetched_at,
        market_count=len(raw_markets),
        signal_count=len(filtered),
        trade_count=len(trades),
    )

    debug = {
        "normalized": len(markets),
        "relationships": len(relationships),
        "opportunities": len(opportunities),
        "filtered": len(filtered),
        "daily_loss_lockout": daily_loss_lockout,
        **filter_debug,
    }

    return {
        "snapshot_path": snapshot_path,
        "market_count": len(raw_markets),
        "signals": len(filtered),
        "trades": len(trades),
        "closed_trades": len(closed_trades),
        "debug": debug,
    }


def run_fixture_pipeline(fixture_path: str, db_path: str) -> dict[str, int]:
    raw_markets = load_raw_fixture_markets(fixture_path)
    result = _run_raw_market_pipeline(
        raw_markets,
        fetched_at="fixture",
        db_path=db_path,
        snapshot_path=fixture_path,
        hold_hours=StrategyConfig().paper_hold_hours,
    )
    return {"signals": result["signals"], "trades": result["trades"]}


def replay_snapshot_pipeline(snapshot_path: Path, db_path: str, hold_hours: int | None = None) -> dict[str, int | str]:
    payload = load_snapshot_file(snapshot_path)
    active_hold_hours = hold_hours if hold_hours is not None else StrategyConfig().paper_hold_hours
    return _run_raw_market_pipeline(
        payload["markets"],
        payload["fetched_at"],
        db_path=db_path,
        snapshot_path=str(snapshot_path),
        hold_hours=active_hold_hours,
    )


def run_live_snapshot_pipeline(
    snapshot_path: Path,
    db_path: str,
    client: object,
    fetched_at: str,
    hold_hours: int | None = None,
) -> dict[str, int | str]:
    raw_markets = client.fetch_markets()
    save_snapshot_file(snapshot_path=snapshot_path, markets=raw_markets, fetched_at=fetched_at)
    active_hold_hours = hold_hours if hold_hours is not None else StrategyConfig().paper_hold_hours
    return _run_raw_market_pipeline(
        raw_markets,
        fetched_at=fetched_at,
        db_path=db_path,
        snapshot_path=str(snapshot_path),
        hold_hours=active_hold_hours,
    )


def run_snapshot_backfill(snapshots_dir: Path, db_path: str) -> dict[str, int]:
    snapshot_count = 0
    total_markets = 0
    total_signals = 0
    total_trades = 0

    for snapshot_path in sorted(snapshots_dir.glob("*.json")):
        result = replay_snapshot_pipeline(snapshot_path=snapshot_path, db_path=db_path)
        snapshot_count += 1
        total_markets += int(result["market_count"])
        total_signals += int(result["signals"])
        total_trades += int(result["trades"])

    return {
        "snapshot_count": snapshot_count,
        "total_markets": total_markets,
        "total_signals": total_signals,
        "total_trades": total_trades,
    }
