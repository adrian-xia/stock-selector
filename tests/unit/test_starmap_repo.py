"""StarMapRepository 映射测试。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.research.repository.starmap_repo import StarMapRepository


@pytest.mark.asyncio
async def test_get_research_overview_normalizes_macro_and_sector_fields() -> None:
    """overview 应输出前端可直接消费的稳定字段形状。"""
    repo = StarMapRepository(AsyncMock())
    repo.get_macro_signal = AsyncMock(return_value=SimpleNamespace(
        risk_appetite="high",
        global_risk_score=Decimal("72.5"),
        macro_summary="风险偏好回升",
        positive_sectors=[
            {"sector_name": "半导体", "reason": "政策催化", "confidence": 0.9},
            {"sector_name": "AI算力", "reason": "订单增长", "confidence": 0.8},
        ],
        negative_sectors=["银行"],
    ))
    repo.get_sector_resonance = AsyncMock(return_value=[
        SimpleNamespace(
            sector_code="885760",
            sector_name="半导体",
            final_score=Decimal("88.6"),
            news_score=Decimal("84.2"),
            moneyflow_score=Decimal("90.1"),
            trend_score=Decimal("86.5"),
            confidence=Decimal("91.0"),
            drivers=["政策催化", "资金净流入"],
        )
    ])
    repo.get_trade_plans = AsyncMock(return_value=[
        SimpleNamespace(
            ts_code="688981.SH",
            stock_name="中芯国际",
            valid_date=date(2026, 3, 7),
            source_strategy="volume-breakout-trigger-v2",
            plan_type="breakout",
            direction="buy",
            trigger_price=Decimal("97.1"),
            stop_loss_price=Decimal("92.2"),
            take_profit_price=Decimal("107.1"),
            risk_reward_ratio=Decimal("2.0"),
            confidence=Decimal("92.3"),
            position_suggestion=Decimal("0.25"),
            market_regime="bull",
            market_risk_score=Decimal("38.5"),
            sector_name="半导体",
            sector_score=Decimal("88.6"),
            entry_rule="突破前高",
            stop_loss_rule="跌破止损",
            take_profit_rule="分批止盈",
            emergency_exit_text="异常离场",
            plan_status="PENDING",
            triggered=False,
            actual_price=None,
            reasoning=["行业共振靠前"],
            risk_flags=[],
        )
    ])

    result = await repo.get_research_overview(date(2026, 3, 6))

    assert result["macro_signal"]["positive_sectors"] == ["半导体", "AI算力"]
    assert result["macro_signal"]["negative_sectors"] == ["银行"]
    assert result["top_sectors"][0]["confidence"] == pytest.approx(91.0)
    assert result["top_sectors"][0]["drivers"] == ["政策催化", "资金净流入"]
    assert result["trade_plans"][0]["market_risk_score"] == pytest.approx(38.5)
    assert result["trade_plans"][0]["reasoning"] == ["行业共振靠前"]
