"""测试 Redis 连接管理：init / get / close 生命周期。"""

from unittest.mock import AsyncMock, patch

import pytest

from app.cache import redis_client


class TestInitRedis:
    """测试 Redis 初始化。"""

    @patch("app.cache.redis_client.aioredis")
    async def test_successful_connection(self, mock_aioredis: AsyncMock) -> None:
        """Redis 可用时应成功初始化。"""
        mock_client = AsyncMock()
        mock_aioredis.from_url.return_value = mock_client

        redis_client._redis_client = None
        await redis_client.init_redis()

        assert redis_client.get_redis() is mock_client
        mock_client.ping.assert_called_once()

        # 清理
        redis_client._redis_client = None

    @patch("app.cache.redis_client.aioredis")
    async def test_connection_failure_degrades(self, mock_aioredis: AsyncMock) -> None:
        """Redis 不可用时应降级，get_redis() 返回 None。"""
        mock_client = AsyncMock()
        mock_client.ping.side_effect = ConnectionError("Connection refused")
        mock_aioredis.from_url.return_value = mock_client

        redis_client._redis_client = None
        await redis_client.init_redis()

        assert redis_client.get_redis() is None

        # 清理
        redis_client._redis_client = None


class TestGetRedis:
    """测试 Redis 客户端获取。"""

    def test_returns_none_when_not_initialized(self) -> None:
        """未初始化时应返回 None。"""
        redis_client._redis_client = None
        assert redis_client.get_redis() is None

    def test_returns_client_when_initialized(self) -> None:
        """已初始化时应返回客户端实例。"""
        mock_client = AsyncMock()
        redis_client._redis_client = mock_client
        assert redis_client.get_redis() is mock_client

        # 清理
        redis_client._redis_client = None


class TestCloseRedis:
    """测试 Redis 连接关闭。"""

    async def test_close_active_connection(self) -> None:
        """关闭活跃连接后 get_redis() 应返回 None。"""
        mock_client = AsyncMock()
        redis_client._redis_client = mock_client

        await redis_client.close_redis()

        mock_client.close.assert_called_once()
        assert redis_client.get_redis() is None

    async def test_close_without_connection(self) -> None:
        """无连接时关闭不应报错。"""
        redis_client._redis_client = None
        await redis_client.close_redis()  # 不应抛异常
        assert redis_client.get_redis() is None
