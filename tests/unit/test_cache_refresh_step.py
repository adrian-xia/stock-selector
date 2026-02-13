"""测试盘后链路缓存刷新步骤。"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.scheduler.jobs import cache_refresh_step, run_post_market_chain


class TestCacheRefreshStep:
    """测试缓存刷新步骤。"""

    @patch("app.scheduler.jobs.get_redis")
    @patch("app.scheduler.jobs.refresh_all_tech_cache", new_callable=AsyncMock)
    async def test_successful_refresh(
        self, mock_refresh: AsyncMock, mock_get_redis: AsyncMock
    ) -> None:
        """Redis 可用时应执行全量刷新。"""
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        mock_refresh.return_value = 5000

        await cache_refresh_step(date(2026, 2, 7))

        mock_refresh.assert_called_once()

    @patch("app.scheduler.jobs.get_redis")
    async def test_skip_when_redis_unavailable(
        self, mock_get_redis: AsyncMock
    ) -> None:
        """Redis 不可用时应跳过。"""
        mock_get_redis.return_value = None

        # 不应抛异常
        await cache_refresh_step(date(2026, 2, 7))

    @patch("app.scheduler.jobs.get_redis")
    @patch("app.scheduler.jobs.refresh_all_tech_cache", new_callable=AsyncMock)
    async def test_refresh_failure_does_not_raise(
        self, mock_refresh: AsyncMock, mock_get_redis: AsyncMock
    ) -> None:
        """刷新失败时不应抛异常。"""
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis
        mock_refresh.side_effect = Exception("Unexpected error")

        # 不应抛异常
        await cache_refresh_step(date(2026, 2, 7))


class TestPostMarketChainWithCache:
    """测试盘后链路中缓存刷新步骤的集成。"""

    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.cache_refresh_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_cache_refresh_called_before_pipeline(
        self,
        mock_build: AsyncMock,
        mock_cache: AsyncMock,
        mock_pipeline: AsyncMock,
    ) -> None:
        """缓存刷新应在策略管道之前执行。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.sync_stock_list.return_value = {"inserted": 0, "updated": 0}
        mock_mgr.reset_stale_status.return_value = 0
        mock_mgr.init_sync_progress.return_value = {"inserted": 0}
        mock_mgr.sync_delisted_status.return_value = {"updated": 0}
        mock_mgr.get_stocks_needing_sync.return_value = []
        mock_mgr.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 1.0,
        }
        mock_build.return_value = mock_mgr

        target = date(2026, 2, 7)
        await run_post_market_chain(target)

        mock_cache.assert_called_once_with(target)
        mock_pipeline.assert_called_once_with(target)

    @patch("app.scheduler.jobs.pipeline_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs.cache_refresh_step", new_callable=AsyncMock)
    @patch("app.scheduler.jobs._build_manager")
    async def test_pipeline_runs_even_if_cache_refresh_fails(
        self,
        mock_build: AsyncMock,
        mock_cache: AsyncMock,
        mock_pipeline: AsyncMock,
    ) -> None:
        """缓存刷新失败不应阻断策略管道。"""
        mock_mgr = AsyncMock()
        mock_mgr.is_trade_day.return_value = True
        mock_mgr.acquire_sync_lock.return_value = True
        mock_mgr.sync_stock_list.return_value = {"inserted": 0, "updated": 0}
        mock_mgr.reset_stale_status.return_value = 0
        mock_mgr.init_sync_progress.return_value = {"inserted": 0}
        mock_mgr.sync_delisted_status.return_value = {"updated": 0}
        mock_mgr.get_stocks_needing_sync.return_value = []
        mock_mgr.get_sync_summary.return_value = {
            "total": 100, "data_done": 100, "indicator_done": 100,
            "failed": 0, "completion_rate": 1.0,
        }
        mock_build.return_value = mock_mgr

        # cache_refresh_step 内部已捕获异常，不会向外抛出
        mock_cache.return_value = None

        target = date(2026, 2, 7)
        await run_post_market_chain(target)

        mock_pipeline.assert_called_once_with(target)
