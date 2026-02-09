"""测试盘后链路的完整步骤顺序（包含交易日历更新）。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.scheduler.jobs import run_post_market_chain


@pytest.mark.asyncio
async def test_post_market_chain_complete_steps_order():
    """测试盘后链路的完整步骤顺序。

    预期顺序：
    1. 交易日历更新
    2. 交易日校验
    3. 日线数据同步
    4. 技术指标计算
    5. 缓存刷新
    6. 策略管道执行
    """
    target = date(2026, 2, 10)
    call_order = []

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager, \
         patch("app.scheduler.jobs.sync_daily_step") as mock_sync_daily, \
         patch("app.scheduler.jobs.indicator_step") as mock_indicator, \
         patch("app.scheduler.jobs.cache_refresh_step") as mock_cache, \
         patch("app.scheduler.jobs.pipeline_step") as mock_pipeline:

        # 模拟 DataManager
        mock_manager = AsyncMock()

        async def sync_calendar_side_effect():
            call_order.append("1_sync_calendar")
            return {"inserted": 100}

        async def is_trade_day_side_effect(date):
            call_order.append("2_is_trade_day")
            return True

        mock_manager.sync_trade_calendar.side_effect = sync_calendar_side_effect
        mock_manager.is_trade_day.side_effect = is_trade_day_side_effect
        mock_build_manager.return_value = mock_manager

        # 模拟其他步骤
        async def sync_daily_side_effect(*args, **kwargs):
            call_order.append("3_sync_daily")

        async def indicator_side_effect(*args, **kwargs):
            call_order.append("4_indicator")

        async def cache_side_effect(*args, **kwargs):
            call_order.append("5_cache")

        async def pipeline_side_effect(*args, **kwargs):
            call_order.append("6_pipeline")

        mock_sync_daily.side_effect = sync_daily_side_effect
        mock_indicator.side_effect = indicator_side_effect
        mock_cache.side_effect = cache_side_effect
        mock_pipeline.side_effect = pipeline_side_effect

        # 执行盘后链路
        await run_post_market_chain(target)

        # 验证步骤顺序
        assert call_order == [
            "1_sync_calendar",
            "2_is_trade_day",
            "3_sync_daily",
            "4_indicator",
            "5_cache",
            "6_pipeline",
        ]


@pytest.mark.asyncio
async def test_post_market_chain_calendar_failure_continues():
    """测试交易日历更新失败时，后续步骤仍然执行。"""
    target = date(2026, 2, 10)
    call_order = []

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager, \
         patch("app.scheduler.jobs.sync_daily_step") as mock_sync_daily, \
         patch("app.scheduler.jobs.indicator_step") as mock_indicator, \
         patch("app.scheduler.jobs.cache_refresh_step") as mock_cache, \
         patch("app.scheduler.jobs.pipeline_step") as mock_pipeline:

        # 模拟 DataManager
        mock_manager = AsyncMock()

        async def sync_calendar_side_effect():
            call_order.append("1_sync_calendar_failed")
            raise Exception("BaoStock API error")

        async def is_trade_day_side_effect(date):
            call_order.append("2_is_trade_day")
            return True

        mock_manager.sync_trade_calendar.side_effect = sync_calendar_side_effect
        mock_manager.is_trade_day.side_effect = is_trade_day_side_effect
        mock_build_manager.return_value = mock_manager

        # 模拟其他步骤
        async def sync_daily_side_effect(*args, **kwargs):
            call_order.append("3_sync_daily")

        async def indicator_side_effect(*args, **kwargs):
            call_order.append("4_indicator")

        async def cache_side_effect(*args, **kwargs):
            call_order.append("5_cache")

        async def pipeline_side_effect(*args, **kwargs):
            call_order.append("6_pipeline")

        mock_sync_daily.side_effect = sync_daily_side_effect
        mock_indicator.side_effect = indicator_side_effect
        mock_cache.side_effect = cache_side_effect
        mock_pipeline.side_effect = pipeline_side_effect

        # 执行盘后链路
        await run_post_market_chain(target)

        # 验证即使交易日历更新失败，后续步骤仍然执行
        assert "1_sync_calendar_failed" in call_order
        assert "2_is_trade_day" in call_order
        assert "3_sync_daily" in call_order
        assert "4_indicator" in call_order
        assert "5_cache" in call_order
        assert "6_pipeline" in call_order
