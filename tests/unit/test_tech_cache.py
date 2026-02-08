"""测试技术指标缓存：命中/未命中、批量读取、全量刷新、预热。"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cache.tech_cache import (
    TechIndicatorCache,
    refresh_all_tech_cache,
    warmup_cache,
)


def _make_session_factory(execute_return=None):
    """构造模拟的 async_sessionmaker，正确支持 async with。"""
    mock_session = AsyncMock()
    if execute_return is not None:
        mock_session.execute.return_value = execute_return

    @asynccontextmanager
    async def fake_factory():
        yield mock_session

    mock_sf = MagicMock(side_effect=fake_factory)
    return mock_sf, mock_session


def _make_redis_mock():
    """构造 Redis mock：同步方法用 MagicMock，异步方法显式设置。"""
    mock = MagicMock()
    mock.hgetall = AsyncMock()
    mock.hset = AsyncMock()
    mock.expire = AsyncMock()
    mock.get = AsyncMock()
    mock.set = AsyncMock()
    mock.ping = AsyncMock()
    return mock


class _AsyncIterator:
    """辅助：将列表包装为异步迭代器。"""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration


class TestGetLatest:
    """测试单只股票缓存读取。"""

    async def test_cache_hit(self) -> None:
        """Redis 有数据时应直接返回，不查 DB。"""
        mock_redis = _make_redis_mock()
        mock_redis.hgetall.return_value = {
            b"ma5": b"1705.20",
            b"rsi6": b"62.50",
        }
        mock_sf = MagicMock()

        cache = TechIndicatorCache(mock_redis, mock_sf)
        result = await cache.get_latest("600519.SH")

        assert result == {"ma5": "1705.20", "rsi6": "62.50"}
        mock_redis.hgetall.assert_called_once_with("tech:600519.SH:latest")
        mock_sf.assert_not_called()

    async def test_cache_miss_fallback_to_db(self) -> None:
        """Redis 无数据时应查 DB 并回填。"""
        mock_redis = _make_redis_mock()
        mock_redis.hgetall.return_value = {}

        mock_row = MagicMock()
        mock_row.fetchone.return_value = None
        mock_sf, _ = _make_session_factory(execute_return=mock_row)

        cache = TechIndicatorCache(mock_redis, mock_sf)
        result = await cache.get_latest("999999.SH")
        assert result is None

    async def test_redis_failure_degrades_to_db(self) -> None:
        """Redis 异常时应静默降级到 DB。"""
        mock_redis = _make_redis_mock()
        mock_redis.hgetall.side_effect = ConnectionError("Redis down")

        mock_row = MagicMock()
        mock_row.fetchone.return_value = None
        mock_sf, _ = _make_session_factory(execute_return=mock_row)

        cache = TechIndicatorCache(mock_redis, mock_sf)
        result = await cache.get_latest("600519.SH")
        assert result is None

    async def test_redis_none_skips_cache(self) -> None:
        """redis_client 为 None 时应直接查 DB。"""
        mock_row = MagicMock()
        mock_row.fetchone.return_value = None
        mock_sf, _ = _make_session_factory(execute_return=mock_row)

        cache = TechIndicatorCache(None, mock_sf)
        result = await cache.get_latest("600519.SH")
        assert result is None


class TestGetBatch:
    """测试批量缓存读取。"""

    async def test_all_cache_hits(self) -> None:
        """全部命中时应通过 Pipeline 一次返回。"""
        mock_redis = _make_redis_mock()
        mock_pipe = MagicMock()
        mock_pipe.hgetall = MagicMock()
        mock_pipe.execute = AsyncMock(return_value=[
            {b"ma5": b"100.00"},
            {b"ma5": b"200.00"},
        ])
        mock_redis.pipeline.return_value = mock_pipe
        mock_sf = MagicMock()

        cache = TechIndicatorCache(mock_redis, mock_sf)
        result = await cache.get_batch(["600519.SH", "000001.SZ"])

        assert "600519.SH" in result
        assert "000001.SZ" in result
        assert result["600519.SH"] == {"ma5": "100.00"}

    async def test_redis_none_falls_back(self) -> None:
        """redis_client 为 None 时应全部回源 DB。"""
        mock_row = MagicMock()
        mock_row.fetchone.return_value = None
        mock_sf, _ = _make_session_factory(execute_return=mock_row)

        cache = TechIndicatorCache(None, mock_sf)
        result = await cache.get_batch(["600519.SH"])
        assert result == {}


class TestRefreshAllTechCache:
    """测试全量刷新。"""

    async def test_refresh_writes_to_redis(self) -> None:
        """应将 DB 数据批量写入 Redis。"""
        mock_redis = _make_redis_mock()
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock()
        mock_redis.pipeline.return_value = mock_pipe

        mock_row = MagicMock()
        row_data = ["600519.SH"] + ["100.00"] * 22 + ["2026-02-07"]
        mock_row.fetchall.return_value = [tuple(row_data)]
        mock_sf, _ = _make_session_factory(execute_return=mock_row)

        count = await refresh_all_tech_cache(mock_redis, mock_sf)

        assert count == 1
        mock_pipe.hset.assert_called_once()
        mock_pipe.expire.assert_called_once()

    async def test_refresh_redis_failure(self) -> None:
        """Redis 不可用时应返回 0，不抛异常。"""
        mock_redis = _make_redis_mock()
        mock_pipe = MagicMock()
        mock_pipe.hset = MagicMock()
        mock_pipe.expire = MagicMock()
        mock_pipe.execute = AsyncMock(side_effect=ConnectionError("down"))
        mock_redis.pipeline.return_value = mock_pipe

        mock_row = MagicMock()
        mock_row.fetchall.return_value = [tuple(["600519.SH"] + ["100"] * 23)]
        mock_sf, _ = _make_session_factory(execute_return=mock_row)

        count = await refresh_all_tech_cache(mock_redis, mock_sf)
        assert count == 0


class TestWarmupCache:
    """测试缓存预热。"""

    async def test_cold_start_triggers_refresh(self) -> None:
        """Redis 无数据时应触发全量刷新。"""
        mock_redis = _make_redis_mock()
        mock_redis.scan_iter = MagicMock(return_value=_AsyncIterator([]))
        mock_sf = MagicMock()

        with patch("app.cache.tech_cache.refresh_all_tech_cache",
                   new_callable=AsyncMock) as mock_refresh:
            mock_refresh.return_value = 5000
            await warmup_cache(mock_redis, mock_sf)
            mock_refresh.assert_called_once_with(mock_redis, mock_sf)

    async def test_warm_start_skips_refresh(self) -> None:
        """Redis 已有足够数据时应跳过刷新。"""
        mock_redis = _make_redis_mock()
        keys = [f"tech:{i}:latest".encode() for i in range(150)]
        mock_redis.scan_iter = MagicMock(return_value=_AsyncIterator(keys))
        mock_sf = MagicMock()

        with patch("app.cache.tech_cache.refresh_all_tech_cache",
                   new_callable=AsyncMock) as mock_refresh:
            await warmup_cache(mock_redis, mock_sf)
            mock_refresh.assert_not_called()

    async def test_warmup_failure_degrades(self) -> None:
        """预热失败时应静默降级。"""
        mock_redis = _make_redis_mock()
        mock_redis.scan_iter = MagicMock(
            side_effect=ConnectionError("Redis down")
        )
        mock_sf = MagicMock()

        await warmup_cache(mock_redis, mock_sf)
