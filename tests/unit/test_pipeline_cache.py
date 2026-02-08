"""测试选股结果缓存读写及降级。"""

import json
from unittest.mock import AsyncMock

import pytest

from app.cache.pipeline_cache import cache_pipeline_result, get_pipeline_result


class TestCachePipelineResult:
    """测试选股结果缓存写入。"""

    async def test_cache_write(self) -> None:
        """应将结果序列化为 JSON 写入 Redis。"""
        mock_redis = AsyncMock()
        result = [{"ts_code": "600519.SH", "score": 85.0}]

        await cache_pipeline_result(mock_redis, "2026-02-07", result)

        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == "pipeline:result:2026-02-07"
        assert json.loads(call_args[0][1]) == result

    async def test_skip_when_redis_none(self) -> None:
        """redis_client 为 None 时应跳过。"""
        await cache_pipeline_result(None, "2026-02-07", [])
        # 不应抛异常

    async def test_redis_failure_degrades(self) -> None:
        """Redis 异常时应静默降级。"""
        mock_redis = AsyncMock()
        mock_redis.set.side_effect = ConnectionError("Redis down")

        # 不应抛异常
        await cache_pipeline_result(mock_redis, "2026-02-07", [{"a": 1}])


class TestGetPipelineResult:
    """测试选股结果缓存读取。"""

    async def test_cache_hit(self) -> None:
        """缓存存在时应返回反序列化结果。"""
        mock_redis = AsyncMock()
        expected = [{"ts_code": "600519.SH", "score": 85.0}]
        mock_redis.get.return_value = json.dumps(expected).encode()

        result = await get_pipeline_result(mock_redis, "2026-02-07")

        assert result == expected
        mock_redis.get.assert_called_once_with("pipeline:result:2026-02-07")

    async def test_cache_miss(self) -> None:
        """缓存不存在时应返回 None。"""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None

        result = await get_pipeline_result(mock_redis, "2026-02-07")
        assert result is None

    async def test_redis_none_returns_none(self) -> None:
        """redis_client 为 None 时应返回 None。"""
        result = await get_pipeline_result(None, "2026-02-07")
        assert result is None

    async def test_redis_failure_returns_none(self) -> None:
        """Redis 异常时应返回 None。"""
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = ConnectionError("Redis down")

        result = await get_pipeline_result(mock_redis, "2026-02-07")
        assert result is None
