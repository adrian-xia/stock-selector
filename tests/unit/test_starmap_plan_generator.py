"""测试 StarMap 增强交易计划生成。"""

from datetime import date

from app.research.planner.plan_generator import generate_trade_plans
from app.research.scoring.market_regime import MarketRegimeResult
from app.research.scoring.stock_rank_fusion import RankedStock


def test_generate_trade_plans_injects_execution_fields_and_risk_flags() -> None:
    """应生成完整执行字段，并在高风险市场打上风险标记。"""
    ranked_stocks = [
        RankedStock(
            ts_code="688981.SH",
            stock_rank=92.5,
            strategy_score_n=78.0,
            sector_score_n=88.0,
            moneyflow_score_n=81.0,
            liquidity_score_n=76.0,
            source_strategies=["volume-breakout-trigger-v2", "volume-price-pattern"],
            sector_name="半导体",
            close=52.30,
        )
    ]
    regime = MarketRegimeResult(
        risk_score=75.0,
        market_regime="bear",
        position_cap=0.30,
        volatility_risk=70.0,
        trend_risk=80.0,
        breadth_risk=75.0,
        sentiment_risk=72.0,
        details={},
    )

    plans = generate_trade_plans(
        ranked_stocks=ranked_stocks,
        market_regime=regime,
        sector_scores={"885760": 88.0},
        trade_date=date(2026, 3, 7),
        valid_date=date(2026, 3, 9),
        max_plans=20,
    )

    assert len(plans) == 1
    plan = plans[0]
    assert plan["trade_date"] == date(2026, 3, 7)
    assert plan["valid_date"] == date(2026, 3, 9)
    assert plan["source_strategy"] == "volume-breakout-trigger-v2"
    assert plan["plan_type"] == "breakout"
    assert plan["direction"] == "buy"
    assert plan["trigger_price"] is not None
    assert plan["stop_loss_price"] is not None
    assert plan["take_profit_price"] is not None
    assert plan["risk_reward_ratio"] == 2.0
    assert plan["position_suggestion"] <= 0.10
    assert "HIGH_MARKET_RISK" in plan["risk_flags"]
    assert any("来源策略" in item for item in plan["reasoning"])


def test_generate_trade_plans_respects_max_plans() -> None:
    """应按 max_plans 截断结果。"""
    stocks = [
        RankedStock(
            ts_code=f"00000{i}.SZ",
            stock_rank=80.0 - i,
            strategy_score_n=45.0,
            sector_score_n=60.0,
            moneyflow_score_n=55.0,
            liquidity_score_n=50.0,
            source_strategies=["pullback-stabilization-trigger-v2"],
            sector_name="电子",
            close=10.0 + i,
        )
        for i in range(5)
    ]
    regime = MarketRegimeResult(
        risk_score=35.0,
        market_regime="bull",
        position_cap=0.90,
        volatility_risk=20.0,
        trend_risk=25.0,
        breadth_risk=30.0,
        sentiment_risk=25.0,
        details={},
    )

    plans = generate_trade_plans(
        ranked_stocks=stocks,
        market_regime=regime,
        sector_scores={},
        trade_date=date(2026, 3, 7),
        valid_date=date(2026, 3, 10),
        max_plans=2,
    )

    assert len(plans) == 2

