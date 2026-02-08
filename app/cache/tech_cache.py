"""技术指标缓存层：Cache-Aside 模式，支持单只/批量读取。"""

import logging
from typing import Optional

import redis.asyncio as aioredis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings

logger = logging.getLogger(__name__)

# 缓存的技术指标字段（对齐 technical_daily 表列名）
INDICATOR_COLUMNS = [
    "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
    "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "rsi6", "rsi12", "rsi24",
    "boll_upper", "boll_mid", "boll_lower",
    "vol_ma5", "vol_ma10", "vol_ratio",
    "atr14", "trade_date",
]


class TechIndicatorCache:
    """技术指标缓存层。

    读取策略：先查 Redis Hash，Miss 则查 DB 并回填。
    所有 Redis 操作均捕获异常，失败时静默降级到 DB。
    """

    def __init__(
        self,
        redis_client: Optional[aioredis.Redis],
        session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        self._redis = redis_client
        self._session_factory = session_factory

    async def get_latest(self, ts_code: str) -> Optional[dict[str, str]]:
        """获取单只股票的最新技术指标。

        Args:
            ts_code: 股票代码，如 "600519.SH"

        Returns:
            指标字典，如 {"ma5": "1705.20", ...}；无数据返回 None
        """
        cache_key = f"tech:{ts_code}:latest"

        # 1. 尝试从 Redis 读取
        if self._redis is not None:
            try:
                data = await self._redis.hgetall(cache_key)
                if data:
                    return {k.decode(): v.decode() for k, v in data.items()}
            except Exception as e:
                logger.warning("Redis 读取失败（%s），回源 DB：%s", cache_key, e)

        # 2. Cache Miss → 查 DB
        logger.debug("Cache miss: %s", cache_key)
        columns_sql = ", ".join(INDICATOR_COLUMNS)
        async with self._session_factory() as session:
            row = await session.execute(
                text(f"""
                    SELECT {columns_sql}
                    FROM technical_daily
                    WHERE ts_code = :code
                    ORDER BY trade_date DESC
                    LIMIT 1
                """),
                {"code": ts_code},
            )
            result = row.fetchone()

        if result is None:
            return None

        # 构建指标字典
        indicator: dict[str, str] = {}
        for i, col in enumerate(INDICATOR_COLUMNS):
            val = result[i]
            if val is not None:
                indicator[col] = str(val)

        # 3. 回填 Redis
        if self._redis is not None and indicator:
            try:
                await self._redis.hset(cache_key, mapping=indicator)
                await self._redis.expire(cache_key, settings.cache_tech_ttl)
            except Exception as e:
                logger.warning("Redis 回填失败（%s）：%s", cache_key, e)

        return indicator

    async def get_batch(
        self, ts_codes: list[str]
    ) -> dict[str, dict[str, str]]:
        """批量获取多只股票的技术指标（Redis Pipeline 优化）。

        Args:
            ts_codes: 股票代码列表

        Returns:
            {ts_code: {指标字典}} 映射
        """
        result: dict[str, dict[str, str]] = {}
        miss_codes: list[str] = []

        # 1. Pipeline 批量查 Redis
        if self._redis is not None:
            try:
                pipe = self._redis.pipeline()
                for code in ts_codes:
                    pipe.hgetall(f"tech:{code}:latest")
                responses = await pipe.execute()

                for code, data in zip(ts_codes, responses):
                    if data:
                        result[code] = {
                            k.decode(): v.decode() for k, v in data.items()
                        }
                    else:
                        miss_codes.append(code)
            except Exception as e:
                logger.warning("Redis 批量读取失败，全部回源 DB：%s", e)
                miss_codes = list(ts_codes)
        else:
            miss_codes = list(ts_codes)

        # 2. 逐只回填 Miss 的
        if miss_codes:
            logger.debug("Cache batch miss: %d codes", len(miss_codes))
            for code in miss_codes:
                indicator = await self.get_latest(code)
                if indicator:
                    result[code] = indicator

        return result


async def refresh_all_tech_cache(
    redis_client: aioredis.Redis,
    session_factory: async_sessionmaker[AsyncSession],
) -> int:
    """全量刷新技术指标缓存（由定时任务在盘后调用）。

    流程：
    1. 从 technical_daily 表查询所有股票的最新指标
    2. 用 Redis Pipeline 批量写入
    3. 设置 TTL

    Args:
        redis_client: Redis 异步客户端
        session_factory: 数据库会话工厂

    Returns:
        刷新的股票数量
    """
    try:
        columns_sql = "ts_code, " + ", ".join(INDICATOR_COLUMNS)
        async with session_factory() as session:
            result = await session.execute(
                text(f"""
                    SELECT DISTINCT ON (ts_code)
                        {columns_sql}
                    FROM technical_daily
                    ORDER BY ts_code, trade_date DESC
                """)
            )
            rows = result.fetchall()

        batch_size = settings.cache_refresh_batch_size
        ttl = settings.cache_tech_ttl
        pipe = redis_client.pipeline()
        count = 0

        for row in rows:
            ts_code = row[0]
            cache_key = f"tech:{ts_code}:latest"
            mapping: dict[str, str] = {}
            for i, col in enumerate(INDICATOR_COLUMNS):
                val = row[i + 1]  # +1 因为第 0 列是 ts_code
                if val is not None:
                    mapping[col] = str(val)
            if mapping:
                pipe.hset(cache_key, mapping=mapping)
                pipe.expire(cache_key, ttl)
                count += 1

            # 每 batch_size 条执行一次，避免 Pipeline 过大
            if count % batch_size == 0 and count > 0:
                await pipe.execute()
                pipe = redis_client.pipeline()

        # 执行剩余
        await pipe.execute()
        logger.info("技术指标缓存刷新完成: %d 只股票", count)
        return count
    except Exception as e:
        logger.warning("技术指标缓存全量刷新失败：%s", e)
        return 0


async def warmup_cache(
    redis_client: aioredis.Redis,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    """应用启动时预热缓存。

    检查 Redis 中是否已有足够的缓存数据（>= 100 条 tech:*:latest），
    不足则执行全量刷新。

    Args:
        redis_client: Redis 异步客户端
        session_factory: 数据库会话工厂
    """
    try:
        logger.info("开始预热缓存...")

        # 检查已有缓存数量
        count = 0
        async for _key in redis_client.scan_iter(match="tech:*:latest", count=200):
            count += 1
            if count >= 100:
                break

        if count >= 100:
            logger.info("Redis 已有缓存数据（>= %d 条），跳过预热", count)
            return

        # 全量刷新
        refreshed = await refresh_all_tech_cache(redis_client, session_factory)
        logger.info("缓存预热完成: %d 只股票", refreshed)
    except Exception as e:
        logger.warning("缓存预热失败，跳过：%s", e)
