"""测试同步锁（Task 4.3）。"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.manager import DataManager


def _make_manager():
    sf = MagicMock()
    return DataManager(
        session_factory=sf,
        clients={"tushare": AsyncMock()},
        primary="tushare",
    )


class TestSyncLock:
    """测试 acquire_sync_lock / release_sync_lock。"""

    @patch("app.cache.redis_client.get_redis")
    async def test_acquire_success(self, mock_get_redis) -> None:
        """Redis SETNX 成功时返回 True。"""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = True
        mock_get_redis.return_value = mock_redis

        mgr = _make_manager()
        result = await mgr.acquire_sync_lock()

        assert result is True
        mock_redis.set.assert_called_once()

    @patch("app.cache.redis_client.get_redis")
    async def test_acquire_occupied(self, mock_get_redis) -> None:
        """锁已被占用时返回 False。"""
        mock_redis = AsyncMock()
        mock_redis.set.return_value = None
        mock_get_redis.return_value = mock_redis

        mgr = _make_manager()
        result = await mgr.acquire_sync_lock()

        assert result is False

    @patch("app.cache.redis_client.get_redis")
    async def test_acquire_no_redis(self, mock_get_redis) -> None:
        """Redis 不可用时降级为无锁模式（返回 True）。"""
        mock_get_redis.return_value = None

        mgr = _make_manager()
        result = await mgr.acquire_sync_lock()

        assert result is True

    @patch("app.cache.redis_client.get_redis")
    async def test_acquire_redis_error(self, mock_get_redis) -> None:
        """Redis 操作异常时降级为无锁模式。"""
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = Exception("Connection refused")
        mock_get_redis.return_value = mock_redis

        mgr = _make_manager()
        result = await mgr.acquire_sync_lock()

        assert result is True

    @patch("app.cache.redis_client.get_redis")
    async def test_release_success(self, mock_get_redis) -> None:
        """释放锁成功。"""
        mock_redis = AsyncMock()
        mock_get_redis.return_value = mock_redis

        mgr = _make_manager()
        await mgr.release_sync_lock()

        mock_redis.delete.assert_called_once_with(DataManager.SYNC_LOCK_KEY)

    @patch("app.cache.redis_client.get_redis")
    async def test_release_no_redis(self, mock_get_redis) -> None:
        """Redis 不可用时释放锁不报错。"""
        mock_get_redis.return_value = None

        mgr = _make_manager()
        await mgr.release_sync_lock()  # 不应抛异常

    @patch("app.cache.redis_client.get_redis")
    async def test_release_redis_error(self, mock_get_redis) -> None:
        """Redis 操作异常时释放锁不报错。"""
        mock_redis = AsyncMock()
        mock_redis.delete.side_effect = Exception("Connection refused")
        mock_get_redis.return_value = mock_redis

        mgr = _make_manager()
        await mgr.release_sync_lock()  # 不应抛异常
