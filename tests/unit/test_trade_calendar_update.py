"""测试盘后链路中的交易日历更新步骤。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from app.scheduler.jobs import run_post_market_chain


@pytest.mark.asyncio
async def test_trade_calendar_update_success():
    """测试交易日历更新成功场景。"""
    target = date(2026, 2, 10)

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager, \
         patch("app.scheduler.jobs.cache_refresh_step") as mock_cache, \
         patch("app.scheduler.jobs.pipeline_step") as mock_pipeline:

        # 模拟 DataManager
        mock_manager = AsyncMock()
        mock_manager.sync_trade_calendar.return_value = {"inserted": 100}
        mock_manager.is_trade_day.return_value = True
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

        mock_cache.return_value = None
        mock_pipeline.return_value = None

        await run_post_market_chain(target)

        # 验证交易日历更新被调用
        mock_manager.sync_trade_calendar.assert_called_once()
        mock_manager.is_trade_day.assert_called_once_with(target)


@pytest.mark.asyncio
async def test_trade_calendar_update_failure_not_blocking():
    """测试交易日历更新失败时不阻断后续步骤。"""
    target = date(2026, 2, 10)

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager, \
         patch("app.scheduler.jobs.cache_refresh_step") as mock_cache, \
         patch("app.scheduler.jobs.pipeline_step") as mock_pipeline:

        mock_manager = AsyncMock()
        mock_manager.sync_trade_calendar.side_effect = Exception("Tushare API error")
        mock_manager.is_trade_day.return_value = True
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

        mock_cache.return_value = None
        mock_pipeline.return_value = None

        # 不应抛出异常
        await run_post_market_chain(target)

        # 验证交易日历更新被调用
        mock_manager.sync_trade_calendar.assert_called_once()
        # 验证后续步骤仍然执行（获取锁、初始化进度等）
        mock_manager.acquire_sync_lock.assert_called_once()
        mock_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_trade_calendar_update_before_trade_day_check():
    """测试交易日历更新在交易日校验之前执行。"""
    target = date(2026, 2, 10)
    call_order = []

    with patch("app.scheduler.jobs._build_manager") as mock_build_manager:
        mock_manager = AsyncMock()

        async def sync_calendar_side_effect():
            call_order.append("sync_calendar")
            return {"inserted": 100}

        async def is_trade_day_side_effect(date):
            call_order.append("is_trade_day")
            return False  # 非交易日，后续步骤不执行

        mock_manager.sync_trade_calendar.side_effect = sync_calendar_side_effect
        mock_manager.is_trade_day.side_effect = is_trade_day_side_effect
        mock_build_manager.return_value = mock_manager

        await run_post_market_chain(target)

        # 验证调用顺序
        assert call_order == ["sync_calendar", "is_trade_day"]
