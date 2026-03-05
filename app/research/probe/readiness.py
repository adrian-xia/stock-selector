"""就绪探针：检查 StarMap 依赖数据是否齐备。

在 Orchestrator 执行前检查：
- 新闻数据是否已抓取
- 宽基指数数据是否就绪
- 必要的行情数据是否完整
"""

import logging
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class ReadinessResult:
    """就绪检查结果。"""

    ready: bool = False
    news_count: int = 0
    index_data_ready: bool = False
    daily_data_ready: bool = False
    missing: list[str] = field(default_factory=list)
    degrade_flags: list[str] = field(default_factory=list)


async def check_readiness(
    session_factory: async_sessionmaker[AsyncSession],
    trade_date: date,
) -> ReadinessResult:
    """检查 StarMap 所需数据就绪度。

    Args:
        session_factory: 数据库会话工厂
        trade_date: 目标交易日

    Returns:
        ReadinessResult 包含就绪状态和降级标记
    """
    result = ReadinessResult()

    async with session_factory() as session:
        # 1. 检查新闻数据（最低 5 条可用新闻）
        try:
            row = await session.execute(
                text(
                    "SELECT COUNT(*) FROM announcements "
                    "WHERE pub_date = :td"
                ),
                {"td": trade_date},
            )
            result.news_count = row.scalar() or 0
            if result.news_count < 5:
                result.degrade_flags.append("LOW_NEWS_COVERAGE")
                logger.warning(
                    "[就绪探针] 新闻不足: %d 条（<5），降级标记", result.news_count
                )
        except Exception:
            result.news_count = 0
            result.degrade_flags.append("NEWS_CHECK_FAILED")

        # 2. 检查指数数据（沪深300 当日行情）
        try:
            row = await session.execute(
                text(
                    "SELECT COUNT(*) FROM raw_tushare_daily "
                    "WHERE trade_date = :td AND ts_code IN "
                    "('000001.SH', '399001.SZ', '000300.SH', '399006.SZ')"
                ),
                {"td": trade_date.strftime("%Y%m%d")},
            )
            index_count = row.scalar() or 0
            result.index_data_ready = index_count >= 3  # 至少 3 个指数有数据
            if not result.index_data_ready:
                result.missing.append("指数行情数据不足")
                result.degrade_flags.append("INDEX_DATA_MISSING")
        except Exception:
            result.degrade_flags.append("INDEX_CHECK_FAILED")

        # 3. 检查个股行情数据（至少 100 只股票有当日数据）
        try:
            row = await session.execute(
                text(
                    "SELECT COUNT(*) FROM stock_daily "
                    "WHERE trade_date = :td"
                ),
                {"td": trade_date},
            )
            daily_count = row.scalar() or 0
            result.daily_data_ready = daily_count >= 100
            if not result.daily_data_ready:
                result.missing.append(f"个股行情数据不足: {daily_count} 只")
                result.degrade_flags.append("DAILY_DATA_SPARSE")
        except Exception:
            result.degrade_flags.append("DAILY_CHECK_FAILED")

    # 综合判断
    critical_flags = {"INDEX_DATA_MISSING", "DAILY_DATA_SPARSE", "INDEX_CHECK_FAILED", "DAILY_CHECK_FAILED"}
    has_critical = bool(set(result.degrade_flags) & critical_flags)
    result.ready = not has_critical

    logger.info(
        "[就绪探针] %s: ready=%s, news=%d, flags=%s",
        trade_date, result.ready, result.news_count, result.degrade_flags,
    )
    return result
