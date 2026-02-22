"""健康检查端点单元测试。"""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.api.health import router, HealthStatus


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    return app


class TestHealthCheck:
    """健康检查端点测试。"""

    @pytest.mark.asyncio
    async def test_all_healthy(self):
        """所有组件正常时返回 healthy。"""
        app = _create_test_app()

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_connect():
            yield mock_conn

        mock_engine.connect = mock_connect

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)

        with patch("app.database.engine", mock_engine), \
             patch("app.cache.redis_client.get_redis", return_value=mock_redis), \
             patch("app.config.settings") as mock_settings:
            mock_settings.tushare_token = "valid-token"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["components"]["database"]["status"] == "up"
        assert data["components"]["redis"]["status"] == "up"
        assert data["components"]["tushare"]["status"] == "configured"

    @pytest.mark.asyncio
    async def test_redis_down_returns_degraded(self):
        """Redis 不可用时返回 degraded。"""
        app = _create_test_app()

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_connect():
            yield mock_conn

        mock_engine.connect = mock_connect

        with patch("app.database.engine", mock_engine), \
             patch("app.cache.redis_client.get_redis", return_value=None), \
             patch("app.config.settings") as mock_settings:
            mock_settings.tushare_token = "valid-token"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["components"]["redis"]["status"] == "down"

    @pytest.mark.asyncio
    async def test_database_down_returns_unhealthy(self):
        """数据库不可用时返回 unhealthy + 503。"""
        app = _create_test_app()

        mock_engine = MagicMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_connect():
            raise ConnectionError("db unreachable")
            yield  # noqa: unreachable

        mock_engine.connect = mock_connect

        with patch("app.database.engine", mock_engine), \
             patch("app.cache.redis_client.get_redis", return_value=None), \
             patch("app.config.settings") as mock_settings:
            mock_settings.tushare_token = "valid-token"

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health")

        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["components"]["database"]["status"] == "down"

    @pytest.mark.asyncio
    async def test_tushare_not_configured(self):
        """Tushare token 未配置时标记 not_configured。"""
        app = _create_test_app()

        mock_engine = MagicMock()
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_connect():
            yield mock_conn

        mock_engine.connect = mock_connect

        with patch("app.database.engine", mock_engine), \
             patch("app.cache.redis_client.get_redis", return_value=None), \
             patch("app.config.settings") as mock_settings:
            mock_settings.tushare_token = ""

            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                resp = await client.get("/health")

        data = resp.json()
        assert data["components"]["tushare"]["status"] == "not_configured"
