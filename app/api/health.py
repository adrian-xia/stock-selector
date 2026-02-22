"""深度健康检查端点。

检测数据库、Redis、Tushare 等关键依赖的可用性，
返回各组件状态和整体健康状态。
"""

import logging
import time
from enum import Enum
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


class HealthStatus(str, Enum):
    """健康状态枚举。"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentStatus(BaseModel):
    """单个组件状态。"""
    status: str  # up / down / configured / not_configured
    latency_ms: float | None = None
    error: str | None = None


class HealthCheckResponse(BaseModel):
    """健康检查响应模型。"""
    status: HealthStatus
    components: dict[str, ComponentStatus]


async def _check_database() -> ComponentStatus:
    """检查数据库连接。"""
    from app.database import engine

    start = time.monotonic()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="up", latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(
            status="down", latency_ms=round(latency, 1), error=str(e)
        )

async def _check_redis() -> ComponentStatus:
    """检查 Redis 连接。"""
    from app.cache.redis_client import get_redis

    redis = get_redis()
    if redis is None:
        return ComponentStatus(status="down", error="Redis 未初始化")

    start = time.monotonic()
    try:
        await redis.ping()
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(status="up", latency_ms=round(latency, 1))
    except Exception as e:
        latency = (time.monotonic() - start) * 1000
        return ComponentStatus(
            status="down", latency_ms=round(latency, 1), error=str(e)
        )


def _check_tushare() -> ComponentStatus:
    """检查 Tushare token 是否配置。"""
    from app.config import settings as _settings

    if _settings.tushare_token and _settings.tushare_token != "your-tushare-token-here":
        return ComponentStatus(status="configured")
    return ComponentStatus(status="not_configured", error="TUSHARE_TOKEN 未配置")


@router.get("/health", response_model=HealthCheckResponse)
async def health_check() -> Any:
    """深度健康检查端点。

    检测数据库、Redis、Tushare 等关键依赖的可用性。

    状态定义：
    - healthy: 所有必需组件正常
    - degraded: 可选组件（Redis）不可用
    - unhealthy: 必需组件（数据库）不可用
    """
    db_status = await _check_database()
    redis_status = await _check_redis()
    tushare_status = _check_tushare()

    components = {
        "database": db_status,
        "redis": redis_status,
        "tushare": tushare_status,
    }

    # 判断整体状态
    if db_status.status != "up":
        overall = HealthStatus.UNHEALTHY
    elif redis_status.status != "up":
        overall = HealthStatus.DEGRADED
    else:
        overall = HealthStatus.HEALTHY

    response = HealthCheckResponse(status=overall, components=components)

    # unhealthy 返回 503
    if overall == HealthStatus.UNHEALTHY:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content=response.model_dump(),
        )

    return response
