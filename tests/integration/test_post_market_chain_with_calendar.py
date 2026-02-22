"""测试盘后链路的完整步骤顺序（包含交易日历更新）。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.scheduler.jobs import run_post_market_chain

# 所有调用 run_post_market_chain 的测试都需要 mock _task_logger
_mock_task_logger = patch("app.scheduler.jobs._task_logger", new_callable=AsyncMock)


@_mock_task_logger
@pytest.mark.asyncio
async def test_post_market_chain_complete_steps_order(mock_tl):
    """测试盘后链路的完整步骤顺序。

    预期顺序：
    1. 交易日历更新
    2. 交易日校验
    3. 获取同步锁
    4. 缓存刷新
    5. 策略管道执行
    """
    target = date(2026, 2, 10)
    call_order = []

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager, \
         patch("app.scheduler.jobs.cache_refresh_step") as mock_cache, \
         patch("app.scheduler.jobs.pipeline_step") as mock_pipeline:

        # 模拟 DataManager
        mock_manager = AsyncMock()

        async def sync_calendar_side_effect():
            call_order.append("1_sync_calendar")
            return {"inserted": 100}

        async def is_trade_day_side_effect(d):
            call_order.append("2_is_trade_day")
            return True

        async def acquire_lock_side_effect():
            call_order.append("3_acquire_lock")
            return True

        mock_manager.sync_trade_calendar.side_effect = sync_calendar_side_effect
        mock_manager.is_trade_day.side_effect = is_trade_day_side_effect
        mock_manager.acquire_sync_lock.side_effect = acquire_lock_side_effect
        mock_manager.sync_stock_list.return_value = {"inserted": 0, "updated": 0}
        mock_manager.reset_stale_status.return_value = 0
        mock_manager.init_sync_progress.return_value = {"inserted": 0}
        mock_manager.sync_delisted_status.return_value = {"updated": 0}
        mock_manager.get_stocks_needing_sync.return_value = []
        mock_manager.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 1.0,
        }
        mock_build_manager.return_value = mock_manager

        # 模拟缓存和策略步骤
        async def cache_side_effect(*args, **kwargs):
            call_order.append("4_cache")

        async def pipeline_side_effect(*args, **kwargs):
            call_order.append("5_pipeline")

        mock_cache.side_effect = cache_side_effect
        mock_pipeline.side_effect = pipeline_side_effect

        # 执行盘后链路
        await run_post_market_chain(target)

        # 验证步骤顺序
        assert call_order == [
            "1_sync_calendar",
            "2_is_trade_day",
            "3_acquire_lock",
            "4_cache",
            "5_pipeline",
        ]


@_mock_task_logger
@pytest.mark.asyncio
async def test_post_market_chain_calendar_failure_continues(mock_tl):
    """测试交易日历更新失败时，后续步骤仍然执行。"""
    target = date(2026, 2, 10)
    call_order = []

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager, \
         patch("app.scheduler.jobs.cache_refresh_step") as mock_cache, \
         patch("app.scheduler.jobs.pipeline_step") as mock_pipeline:

        # 模拟 DataManager
        mock_manager = AsyncMock()

        async def sync_calendar_side_effect():
            call_order.append("1_sync_calendar_failed")
            raise Exception("Tushare API error")

        async def is_trade_day_side_effect(d):
            call_order.append("2_is_trade_day")
            return True

        mock_manager.sync_trade_calendar.side_effect = sync_calendar_side_effect
        mock_manager.is_trade_day.side_effect = is_trade_day_side_effect
        mock_manager.acquire_sync_lock.return_value = True
        mock_manager.sync_stock_list.return_value = {"inserted": 0, "updated": 0}
        mock_manager.reset_stale_status.return_value = 0
        mock_manager.init_sync_progress.return_value = {"inserted": 0}
        mock_manager.sync_delisted_status.return_value = {"updated": 0}
        mock_manager.get_stocks_needing_sync.return_value = []
        mock_manager.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 1.0,
        }
        mock_build_manager.return_value = mock_manager

        # 模拟缓存和策略步骤
        async def cache_side_effect(*args, **kwargs):
            call_order.append("3_cache")

        async def pipeline_side_effect(*args, **kwargs):
            call_order.append("4_pipeline")

        mock_cache.side_effect = cache_side_effect
        mock_pipeline.side_effect = pipeline_side_effect

        # 执行盘后链路
        await run_post_market_chain(target)

        # 验证即使交易日历更新失败，后续步骤仍然执行
        assert "1_sync_calendar_failed" in call_order
        assert "2_is_trade_day" in call_order
        assert "3_cache" in call_order
        assert "4_pipeline" in call_order
