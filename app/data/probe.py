"""数据嗅探模块：轻量级检测指定日期的数据是否就绪。

通过查询少量样本股票来判断数据源是否已更新当日数据，避免全量查询的性能开销。
"""

import logging
import time
from datetime import date

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.market import StockDaily

logger = logging.getLogger(__name__)


async def probe_daily_data(
    session_factory: async_sessionmaker,
    target_date: date,
    probe_stocks: list[str],
    threshold: float = 0.8,
) -> bool:
    """嗅探指定日期的数据是否就绪。

    通过查询样本股票在目标日期是否有数据来判断数据源是否已更新。
    如果 ≥ threshold（默认 80%）的样本股票有数据，则认为数据已就绪。

    Args:
        session_factory: 数据库会话工厂
        target_date: 目标日期
        probe_stocks: 样本股票代码列表，如 ["600519.SH", "000001.SZ"]
        threshold: 成功阈值，默认 0.8（80%）

    Returns:
        True 表示数据已就绪，False 表示数据未就绪

    Examples:
        >>> # 查询 5 只样本股票，其中 4 只有数据（80%）
        >>> result = await probe_daily_data(
        ...     session_factory,
        ...     date(2026, 2, 10),
        ...     ["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
        ...     threshold=0.8,
        ... )
        >>> result
        True
    """
    if not probe_stocks:
        logger.warning("[数据嗅探] 样本股票列表为空，返回 False")
        return False

    # 性能计时
    start_time = time.monotonic()

    async with session_factory() as session:
        # 查询样本股票在目标日期有数据的数量
        # 使用 idx_stock_daily_code_date 索引优化查询性能
        stmt = (
            select(func.count(StockDaily.ts_code.distinct()))
            .where(
                StockDaily.ts_code.in_(probe_stocks),
                StockDaily.trade_date == target_date,
            )
        )
        result = await session.execute(stmt)
        count = result.scalar() or 0

    elapsed = time.monotonic() - start_time

    # 计算成功率
    total = len(probe_stocks)
    success_rate = count / total if total > 0 else 0.0
    is_ready = success_rate >= threshold

    # 记录嗅探结果
    logger.info(
        "[数据嗅探] 日期 %s: %d/%d 样本有数据 (%.1f%%)，阈值 %.1f%%，结果: %s，耗时 %.2fms",
        target_date,
        count,
        total,
        success_rate * 100,
        threshold * 100,
        "就绪" if is_ready else "未就绪",
        elapsed * 1000,
    )

    return is_ready
