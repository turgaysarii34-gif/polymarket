from polymarket_bot.execution.paper_engine import close_paper_trades, open_paper_trades
from polymarket_bot.normalization.normalize import normalize_markets
from polymarket_bot.relationships.engine import infer_relationships
from polymarket_bot.risk.filters import filter_opportunities
from polymarket_bot.signals.scorer import score_opportunities


def test_close_paper_trades_marks_positions_closed_with_realized_pnl(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    trades = open_paper_trades(filtered[:1], markets)

    closed = close_paper_trades(trades, exit_price=0.72)

    assert closed[0].status == "closed"
    assert closed[0].realized_pnl > 0
    assert closed[0].exit_price == 0.72


def test_open_paper_trades_creates_position_with_fill_and_fees(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(filtered[:1], markets)

    assert len(trades) == 1
    assert trades[0].status == "open"
    assert trades[0].fill_price > 0
    assert trades[0].estimated_fee > 0


def test_open_paper_trades_selects_top_five_by_score_and_sizes_from_bankroll(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 3

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 5
    assert all(trade.allocated_notional == 10.0 for trade in trades)
    assert trades[0].score_at_entry >= trades[-1].score_at_entry


def test_open_paper_trades_stops_when_run_allocation_cap_is_hit(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 3

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=100.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 5
    assert sum(trade.allocated_notional for trade in trades) == 10.0
    assert all(trade.allocated_notional == 2.0 for trade in trades)
    assert all(trade.bankroll_at_entry == 100.0 for trade in trades)
    assert all(trade.opened_at == "2026-04-08T12:00:00Z" for trade in trades)


def test_open_paper_trades_breaks_when_per_trade_notional_exceeds_run_budget(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=100.0,
        max_trades=5,
        max_run_allocation=0.01,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_open_paper_trades_returns_descending_score_order(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = list(reversed(filtered)) * 3

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    scores = [trade.score_at_entry for trade in trades]
    assert scores == sorted(scores, reverse=True)
    assert all(trade.relation_type for trade in trades)
    assert all(trade.opened_at == "2026-04-08T12:00:00Z" for trade in trades)
    assert all(trade.bankroll_at_entry == 500.0 for trade in trades)


def test_open_paper_trades_returns_empty_for_no_opportunities(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)

    trades = open_paper_trades(
        [],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_open_paper_trades_limits_result_count_to_max_trades(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 10

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=3,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 3
    assert all(trade.allocated_notional == 10.0 for trade in trades)
    assert sum(trade.allocated_notional for trade in trades) == 30.0


def test_open_paper_trades_uses_current_bankroll_for_compound_sizing(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=525.0,
        max_trades=1,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].allocated_notional == 10.5
    assert trades[0].estimated_fee == 0.21
    assert trades[0].bankroll_at_entry == 525.0
    assert trades[0].score_at_entry == filtered[0].score
    assert trades[0].relation_type == filtered[0].relation_type


def test_open_paper_trades_respects_budget_before_max_count(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 10

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=250.0,
        max_trades=10,
        max_run_allocation=0.04,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 2
    assert sum(trade.allocated_notional for trade in trades) == 10.0
    assert all(trade.allocated_notional == 5.0 for trade in trades)


def test_open_paper_trades_defaults_match_legacy_shape(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(filtered[:1], markets)

    assert len(trades) == 1
    assert trades[0].status == "open"
    assert trades[0].opened_at == ""
    assert trades[0].score_at_entry == 0.0
    assert trades[0].bankroll_at_entry == 0.0
    assert trades[0].relation_type == ""
    assert trades[0].allocated_notional == 100.0
    assert trades[0].estimated_fee == 2.0
    assert trades[0].fill_price > 0
    assert trades[0].estimated_fee > 0


def test_open_paper_trades_legacy_call_still_works(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(filtered[:2], markets)

    assert len(trades) == 2
    assert all(trade.allocated_notional == 100.0 for trade in trades)
    assert all(trade.status == "open" for trade in trades)
    assert all(trade.relation_type == "" for trade in trades)
    assert all(trade.opened_at == "" for trade in trades)
    assert all(trade.score_at_entry == 0.0 for trade in trades)
    assert all(trade.bankroll_at_entry == 0.0 for trade in trades)
    assert all(trade.fill_price > 0 for trade in trades)
    assert all(trade.estimated_fee > 0 for trade in trades)


def test_open_paper_trades_uses_score_sorted_subset_when_max_trades_is_small(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = list(reversed(filtered)) * 4

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=2,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    selected_scores = [trade.score_at_entry for trade in trades]
    expected_scores = sorted((item.score for item in expanded), reverse=True)[:2]
    assert selected_scores == expected_scores
    assert len(trades) == 2
    assert all(trade.allocated_notional == 10.0 for trade in trades)


def test_open_paper_trades_keeps_existing_fill_formula_under_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    left = {market.market_id: market for market in markets}[filtered[0].left_market_id]
    right = {market.market_id: market for market in markets}[filtered[0].right_market_id]
    expected_fill = round(((left.yes_price + right.yes_price) / 2) + 0.01, 6)

    assert trades[0].fill_price == expected_fill
    assert trades[0].estimated_fee == 0.2
    assert trades[0].allocated_notional == 10.0


def test_open_paper_trades_creates_position_with_fill_and_fees_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].status == "open"
    assert trades[0].fill_price > 0
    assert trades[0].estimated_fee > 0
    assert trades[0].allocated_notional == 10.0
    assert trades[0].score_at_entry == filtered[0].score
    assert trades[0].relation_type == filtered[0].relation_type
    assert trades[0].opened_at == "2026-04-08T12:00:00Z"
    assert trades[0].bankroll_at_entry == 500.0
    assert trades[0].estimated_fee == 0.2


def test_open_paper_trades_handles_fractional_bankroll_precisely(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=437.5,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].allocated_notional == 8.75
    assert trades[0].estimated_fee == 0.175
    assert trades[0].bankroll_at_entry == 437.5


def test_close_paper_trades_preserves_new_entry_metadata(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    closed = close_paper_trades(trades, exit_price=0.72)

    assert closed[0].relation_type == trades[0].relation_type
    assert closed[0].opened_at == trades[0].opened_at
    assert closed[0].score_at_entry == trades[0].score_at_entry
    assert closed[0].bankroll_at_entry == trades[0].bankroll_at_entry
    assert closed[0].status == "closed"
    assert closed[0].realized_pnl > 0
    assert closed[0].exit_price == 0.72
    assert closed[0].closed_at is None
    assert closed[0].exit_snapshot_path is None


def test_open_paper_trades_sorts_before_budget_check(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = list(reversed(filtered)) * 4

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=250.0,
        max_trades=10,
        max_run_allocation=0.04,
        opened_at="2026-04-08T12:00:00Z",
    )

    selected_scores = [trade.score_at_entry for trade in trades]
    assert selected_scores == sorted(selected_scores, reverse=True)
    assert len(trades) == 2
    assert sum(trade.allocated_notional for trade in trades) == 10.0


def test_open_paper_trades_max_trades_zero_returns_empty(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=500.0,
        max_trades=0,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_open_paper_trades_zero_bankroll_returns_empty_under_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=0.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_open_paper_trades_negative_run_allocation_returns_empty(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=-0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_open_paper_trades_preserves_selected_relationship_keys(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = list(reversed(filtered)) * 4

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=3,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    expected_keys = [item.relationship_key for item in sorted(expanded, key=lambda item: item.score, reverse=True)[:3]]
    assert [trade.relationship_key for trade in trades] == expected_keys


def test_open_paper_trades_sets_fee_from_sized_notional(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=750.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].allocated_notional == 15.0
    assert trades[0].estimated_fee == 0.3


def test_close_paper_trades_uses_sized_notional_for_realized_pnl(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    closed = close_paper_trades(trades, exit_price=0.72)
    expected = round((0.72 - trades[0].fill_price) * trades[0].allocated_notional - trades[0].estimated_fee, 6)

    assert closed[0].realized_pnl == expected
    assert closed[0].allocated_notional == 10.0
    assert closed[0].estimated_fee == 0.2


def test_open_paper_trades_budget_cap_with_fractional_trade_notional(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 10

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=437.5,
        max_trades=20,
        max_run_allocation=0.04,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 2
    assert all(trade.allocated_notional == 8.75 for trade in trades)
    assert sum(trade.allocated_notional for trade in trades) == 17.5


def test_open_paper_trades_truncates_to_budget_even_with_large_max_trades(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 20

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=50,
        max_run_allocation=0.02,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].allocated_notional == 10.0


def test_open_paper_trades_keeps_relation_type_from_signal_under_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:2],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert [trade.relation_type for trade in trades] == [item.relation_type for item in filtered[:2]]


def test_open_paper_trades_keeps_relationship_keys_after_sorting_and_truncation(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = list(reversed(filtered)) * 10

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    expected = [item.relationship_key for item in sorted(expanded, key=lambda item: item.score, reverse=True)[:5]]
    assert [trade.relationship_key for trade in trades] == expected


def test_open_paper_trades_per_trade_notional_rounds_to_six_decimals(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=333.333333,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].allocated_notional == round(333.333333 * 0.02, 6)
    assert trades[0].estimated_fee == round(trades[0].allocated_notional * 0.02, 6)


def test_open_paper_trades_run_budget_rounds_to_six_decimals(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 20

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=333.333333,
        max_trades=20,
        max_run_allocation=0.02,
        opened_at="2026-04-08T12:00:00Z",
    )

    run_budget = round(333.333333 * 0.02, 6)
    assert sum(trade.allocated_notional for trade in trades) <= run_budget
    assert len(trades) == 1


def test_open_paper_trades_preserves_existing_market_lookup_logic(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades[0].left_market_id == filtered[0].left_market_id
    assert trades[0].right_market_id == filtered[0].right_market_id
    assert trades[0].relationship_key == filtered[0].relationship_key


def test_open_paper_trades_empty_after_truncation_when_budget_zero(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.0,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_close_paper_trades_preserves_opened_at_for_compound_positions(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    closed = close_paper_trades(trades, exit_price=0.72)

    assert closed[0].opened_at == "2026-04-08T12:00:00Z"
    assert closed[0].bankroll_at_entry == 500.0
    assert closed[0].score_at_entry == filtered[0].score
    assert closed[0].relation_type == filtered[0].relation_type


def test_open_paper_trades_fee_scales_with_notional_under_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    small = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]
    large = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=1000.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]

    assert small.allocated_notional == 10.0
    assert large.allocated_notional == 20.0
    assert small.estimated_fee == 0.2
    assert large.estimated_fee == 0.4


def test_open_paper_trades_truncation_uses_sorted_signal_scores(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = list(reversed(filtered)) * 5

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=4,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    expected_scores = sorted((item.score for item in expanded), reverse=True)[:4]
    assert [trade.score_at_entry for trade in trades] == expected_scores


def test_open_paper_trades_keeps_fill_price_rounding_under_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trade = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=1,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]

    assert trade.fill_price == round(trade.fill_price, 6)
    assert trade.estimated_fee == round(trade.estimated_fee, 6)


def test_close_paper_trades_keeps_closed_at_and_exit_snapshot_defaults_when_not_provided(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trade = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=1,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]
    closed = close_paper_trades([trade], exit_price=0.72)[0]

    assert closed.closed_at is None
    assert closed.exit_snapshot_path is None
    assert closed.status == "closed"
    assert closed.exit_price == 0.72


def test_open_paper_trades_per_trade_allocation_equals_two_percent(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trade = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=1,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]

    assert trade.allocated_notional == 500.0 * 0.02


def test_open_paper_trades_total_deployment_never_exceeds_run_cap(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 50

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=50,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert sum(trade.allocated_notional for trade in trades) <= 500.0 * 0.20


def test_open_paper_trades_respects_top_five_even_when_more_budget_available(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 50

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=5000.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 5


def test_open_paper_trades_budget_check_uses_per_trade_notional_not_legacy_default(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=250.0,
        max_trades=10,
        max_run_allocation=0.02,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 1
    assert trades[0].allocated_notional == 5.0


def test_open_paper_trades_stores_signal_metadata_on_each_trade(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered[:2],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    for trade, signal in zip(trades, filtered[:2]):
        assert trade.relationship_key == signal.relationship_key
        assert trade.relation_type == signal.relation_type
        assert trade.score_at_entry == signal.score
        assert trade.bankroll_at_entry == 500.0
        assert trade.opened_at == "2026-04-08T12:00:00Z"


def test_close_paper_trades_keeps_entry_metadata_after_closing(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    opened = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )
    closed = close_paper_trades(opened, exit_price=0.72)

    assert closed[0].relationship_key == opened[0].relationship_key
    assert closed[0].relation_type == opened[0].relation_type
    assert closed[0].score_at_entry == opened[0].score_at_entry
    assert closed[0].bankroll_at_entry == opened[0].bankroll_at_entry
    assert closed[0].opened_at == opened[0].opened_at
    assert closed[0].status == "closed"
    assert closed[0].exit_price == 0.72
    assert closed[0].realized_pnl > 0


def test_open_paper_trades_returns_exactly_requested_count_when_budget_allows(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered * 20

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=4,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert len(trades) == 4
    assert sum(trade.allocated_notional for trade in trades) == 40.0


def test_open_paper_trades_zero_max_run_allocation_blocks_all_entries(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trades = open_paper_trades(
        filtered,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.0,
        opened_at="2026-04-08T12:00:00Z",
    )

    assert trades == []


def test_open_paper_trades_preserves_right_and_left_market_ids_under_compound_mode(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trade = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]

    assert trade.left_market_id == filtered[0].left_market_id
    assert trade.right_market_id == filtered[0].right_market_id


def test_close_paper_trades_realized_pnl_uses_updated_allocated_notional(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trade = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=750.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]
    closed = close_paper_trades([trade], exit_price=0.72)[0]

    expected = round((0.72 - trade.fill_price) * trade.allocated_notional - trade.estimated_fee, 6)
    assert closed.realized_pnl == expected


def test_open_paper_trades_returns_trades_in_selected_score_order_even_with_duplicates(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())
    expanded = filtered + list(reversed(filtered)) + filtered

    trades = open_paper_trades(
        expanded,
        markets,
        bankroll=500.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )

    scores = [trade.score_at_entry for trade in trades]
    assert scores == sorted(scores, reverse=True)


def test_open_paper_trades_fill_and_fee_remain_positive_under_small_bankroll(raw_fixture_markets):
    markets = normalize_markets(raw_fixture_markets)
    relationships = infer_relationships(markets)
    opportunities = score_opportunities(markets, relationships)
    filtered = filter_opportunities(opportunities, markets, seen_keys=set())

    trade = open_paper_trades(
        filtered[:1],
        markets,
        bankroll=50.0,
        max_trades=5,
        max_run_allocation=0.20,
        opened_at="2026-04-08T12:00:00Z",
    )[0]

    assert trade.allocated_notional == 1.0
    assert trade.estimated_fee == 0.02
    assert trade.fill_price > 0
