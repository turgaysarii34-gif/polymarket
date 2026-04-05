from polymarket_bot.analytics.reporting import summarize_relation_type_pnl
from polymarket_bot.analytics.store import initialize_db, insert_trade_rows
from polymarket_bot.domain.trade import PaperTrade


def test_summarize_relation_type_pnl_groups_results(tmp_path):
    db_path = tmp_path / "analytics.db"
    initialize_db(str(db_path))
    insert_trade_rows(
        str(db_path),
        [
            PaperTrade(
                relationship_key="a:b:mutually_exclusive",
                left_market_id="a",
                right_market_id="b",
                status="closed",
                fill_price=0.55,
                estimated_fee=2.0,
                allocated_notional=100.0,
            )
        ],
    )

    summary = summarize_relation_type_pnl(str(db_path))

    assert summary == [{"relation_type": "mutually_exclusive", "trade_count": 1, "gross_notional": 100.0}]
