"""测试统一计划层相关 API。"""

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.strategy import _build_trade_plan_response, generate_trade_plan


def test_build_trade_plan_response_maps_starmap_fields() -> None:
    """StarMap ORM 记录应被正确映射到 API 响应。"""
    row = SimpleNamespace(
        id=1,
        ts_code="600519.SH",
        trade_date=date(2026, 3, 7),
        valid_date=date(2026, 3, 9),
        direction="buy",
        plan_type="breakout",
        entry_rule="突破前高后回踩确认不破，放量站稳",
        trigger_price=Decimal("1705.5000"),
        stop_loss_price=Decimal("1671.3900"),
        take_profit_price=Decimal("1773.7200"),
        risk_reward_ratio=Decimal("2.0000"),
        source_strategy="volume-breakout-trigger-v2",
        confidence=Decimal("92.3000"),
        triggered=False,
        actual_price=None,
        plan_status="PENDING",
        market_regime="bull",
        position_suggestion=Decimal("0.2500"),
        stop_loss_rule="跌破突破位 5%",
        take_profit_rule="盈利 8% 减半仓，15% 清仓",
        risk_flags=["HIGH_MARKET_RISK"],
    )

    response = _build_trade_plan_response(row)

    assert response.plan_date == date(2026, 3, 7)
    assert response.valid_date == date(2026, 3, 9)
    assert response.trigger_type == "breakout"
    assert response.trigger_price == pytest.approx(1705.5)
    assert response.stop_loss == pytest.approx(1671.39)
    assert response.take_profit == pytest.approx(1773.72)
    assert response.source_strategy == "volume-breakout-trigger-v2"
    assert response.risk_flags == ["HIGH_MARKET_RISK"]


@pytest.mark.asyncio
@patch(
    "app.research.repository.starmap_repo.StarMapRepository.get_trade_plans",
    new_callable=AsyncMock,
)
@patch("app.scheduler.starmap_job.starmap_job", new_callable=AsyncMock)
@patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
async def test_generate_trade_plan_runs_pipeline_and_starmap(
    mock_pipeline_step: AsyncMock,
    mock_starmap_job: AsyncMock,
    mock_get_trade_plans: AsyncMock,
) -> None:
    """生成计划接口应串起选股链和 StarMap。"""
    mock_pipeline_step.return_value = ["pick1", "pick2"]
    mock_starmap_job.return_value = {"status": "success"}
    mock_get_trade_plans.return_value = [MagicMock(), MagicMock(), MagicMock()]

    result = await generate_trade_plan(date(2026, 3, 7))

    assert result == {
        "target_date": "2026-03-07",
        "generated": 3,
        "picks": 2,
        "starmap_status": "success",
    }
    mock_pipeline_step.assert_awaited_once_with(date(2026, 3, 7))
    mock_starmap_job.assert_awaited_once_with(date(2026, 3, 7))
    mock_get_trade_plans.assert_awaited_once_with(date(2026, 3, 7))
