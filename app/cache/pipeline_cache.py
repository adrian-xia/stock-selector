"""选股结果缓存：Pipeline 执行后写入，按日期读取。"""

import json
import logging
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


async def cache_pipeline_result(
    redis_client: Optional[aioredis.Redis],
    trade_date: str,
    result: list[dict],
) -> None:
    """缓存当日选股结果。

    Args:
        redis_client: Redis 异步客户端，None 则跳过
        trade_date: 交易日期，如 "2026-02-07"
        result: 选股结果列表
    """
    if redis_client is None:
        return
    try:
        cache_key = f"pipeline:result:{trade_date}"
        await redis_client.set(
            cache_key,
            json.dumps(result, ensure_ascii=False),
            ex=settings.cache_pipeline_result_ttl,
        )
        logger.debug("选股结果已缓存：%s（%d 条）", cache_key, len(result))
    except Exception as e:
        logger.warning("选股结果缓存写入失败：%s", e)


async def get_pipeline_result(
    redis_client: Optional[aioredis.Redis],
    trade_date: str,
) -> Optional[list[dict]]:
    """获取缓存的选股结果。

    Args:
        redis_client: Redis 异步客户端，None 则返回 None
        trade_date: 交易日期，如 "2026-02-07"

    Returns:
        选股结果列表，无缓存返回 None
    """
    if redis_client is None:
        return None
    try:
        cache_key = f"pipeline:result:{trade_date}"
        data = await redis_client.get(cache_key)
        if data:
            return json.loads(data)
        return None
    except Exception as e:
        logger.warning("选股结果缓存读取失败：%s", e)
        return None
