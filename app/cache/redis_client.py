"""Redis 异步连接管理：init / get / close 三函数，模块级单例。"""

import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

# 模块级单例
_redis_client: Optional[aioredis.Redis] = None


async def init_redis() -> None:
    """初始化 Redis 异步连接。

    在 FastAPI lifespan 启动时调用。
    Redis 不可用时捕获异常并降级，不阻断应用启动。
    """
    global _redis_client
    try:
        url = f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
        if settings.redis_password:
            url = (
                f"redis://:{settings.redis_password}"
                f"@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
            )
        _redis_client = aioredis.from_url(
            url,
            decode_responses=False,
            socket_timeout=5.0,
            socket_connect_timeout=2.0,
            retry_on_timeout=True,
        )
        # 验证连接可用
        await _redis_client.ping()
        logger.info("Redis 连接成功：%s:%s/%s", settings.redis_host, settings.redis_port, settings.redis_db)
    except Exception as e:
        logger.warning("Redis 连接失败，缓存功能降级：%s", e)
        _redis_client = None


def get_redis() -> Optional[aioredis.Redis]:
    """获取 Redis 客户端实例，未初始化或连接失败时返回 None。"""
    return _redis_client


async def close_redis() -> None:
    """关闭 Redis 连接，释放资源。"""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis 连接已关闭")
