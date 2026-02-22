"""FastAPI 请求性能监控中间件。

记录每个 HTTP 请求的响应时间、状态码、路径等性能指标，
超过阈值的慢请求记录 WARNING 日志。
"""

import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.config import settings

logger = logging.getLogger(__name__)

# 不记录性能日志的路径（避免噪音）
_EXCLUDED_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class RequestPerformanceMiddleware(BaseHTTPMiddleware):
    """请求性能日志中间件。

    记录每个请求的 method、path、status_code、duration_ms、client_ip。
    超过慢请求阈值的请求记录 WARNING 日志。
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # 排除噪音路径
        if request.url.path in _EXCLUDED_PATHS:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = (time.monotonic() - start) * 1000

        method = request.method
        path = request.url.path
        status_code = response.status_code
        client_ip = request.client.host if request.client else "-"

        if duration_ms > settings.api_slow_request_threshold_ms:
            logger.warning(
                "[慢请求] %s %s status=%d duration=%.0fms client=%s",
                method, path, status_code, duration_ms, client_ip,
            )
        else:
            logger.info(
                "[请求] %s %s status=%d duration=%.0fms client=%s",
                method, path, status_code, duration_ms, client_ip,
            )

        return response
