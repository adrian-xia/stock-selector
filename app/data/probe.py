"""数据嗅探模块：轻量级检测指定日期的数据是否就绪。

通过调用 Tushare API 查询少量样本股票来判断数据源是否已更新当日数据。
避免查询本地数据库造成的死锁问题（本地数据需要盘后链路同步）。
"""

import logging
import time
from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker

from app.data.tushare import TushareClient

logger = logging.getLogger(__name__)


async def probe_daily_data(
    session_factory: async_sessionmaker,
    target_date: date,
    probe_stocks: list[str],
    threshold: float = 0.8,
) -> bool:
    """嗅探指定日期的数据是否就绪。

    通过调用 Tushare API 查询样本股票在目标日期是否有数据来判断数据源是否已更新。
    如果 ≥ threshold（默认 80%）的样本股票有数据，则认为数据已就绪。

    注意：此函数检查的是 Tushare API 数据源，而不是本地数据库。
    这样可以避免"等待自己先有数据"的死锁问题。

    Args:
        session_factory: 数据库会话工厂（保留参数以兼容现有调用）
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

    # 使用 TushareClient 查询 API 数据
    client = TushareClient()
    trade_date_str = target_date.strftime("%Y%m%d")

    try:
        # 查询全市场当日数据（一次 API 调用）
        records = await client.fetch_raw_daily(trade_date=trade_date_str)

        # 提取所有股票代码
        available_codes = {record.get("ts_code") for record in records if record.get("ts_code")}

        # 统计样本股票中有多少在返回结果中
        count = sum(1 for ts_code in probe_stocks if ts_code in available_codes)

    except Exception as e:
        logger.error(
            "[数据嗅探] 查询 Tushare API 失败: %s",
            str(e),
        )
        return False

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
