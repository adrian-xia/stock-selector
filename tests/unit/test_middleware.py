"""API 性能中间件单元测试。"""

import logging

import pytest
from httpx import ASGITransport, AsyncClient
from fastapi import FastAPI

from app.api.middleware import RequestPerformanceMiddleware


def _create_test_app() -> FastAPI:
    """创建测试用 FastAPI 应用。"""
    app = FastAPI()
    app.add_middleware(RequestPerformanceMiddleware)

    @app.get("/api/v1/test")
    async def test_endpoint():
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.get("/docs")
    async def docs():
        return {"status": "ok"}

    return app


class TestRequestPerformanceMiddleware:
    """请求性能中间件测试。"""

    @pytest.mark.asyncio
    async def test_normal_request_logged(self, caplog):
        """正常请求应记录 INFO 日志。"""
        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with caplog.at_level(logging.INFO, logger="app.api.middleware"):
                response = await client.get("/api/v1/test")

        assert response.status_code == 200
        assert any("[请求]" in r.message and "GET" in r.message for r in caplog.records)

    @pytest.mark.asyncio
    async def test_excluded_path_not_logged(self, caplog):
        """排除路径不应记录性能日志。"""
        app = _create_test_app()
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            with caplog.at_level(logging.DEBUG, logger="app.api.middleware"):
                await client.get("/health")

        middleware_records = [
            r for r in caplog.records if r.name == "app.api.middleware"
        ]
        assert len(middleware_records) == 0

    @pytest.mark.asyncio
    async def test_slow_request_warning(self, caplog):
        """慢请求应记录 WARNING 日志。"""
        app = _create_test_app()

        # 设置极低阈值触发慢请求告警
        from app.config import settings
        original = settings.api_slow_request_threshold_ms
        settings.api_slow_request_threshold_ms = 0
        try:
            async with AsyncClient(
                transport=ASGITransport(app=app), base_url="http://test"
            ) as client:
                with caplog.at_level(logging.WARNING, logger="app.api.middleware"):
                    await client.get("/api/v1/test")

            warning_records = [
                r for r in caplog.records
                if r.levelno >= logging.WARNING and "慢请求" in r.message
            ]
            assert len(warning_records) > 0
        finally:
            settings.api_slow_request_threshold_ms = original
