"""统一新闻采集入口：并行调用 3 个数据源。"""

import asyncio
import logging
from datetime import date

from app.data.sources.eastmoney import EastMoneyCrawler
from app.data.sources.taoguba import TaogubaCrawler
from app.data.sources.xueqiu import XueqiuCrawler

logger = logging.getLogger(__name__)


async def fetch_all_news(
    ts_codes: list[str],
    target_date: date,
) -> list[dict]:
    """并行调用 3 个数据源采集新闻，合并返回。

    单个数据源失败不影响其他数据源。

    Args:
        ts_codes: 股票代码列表
        target_date: 目标日期

    Returns:
        合并后的新闻字典列表
    """
    crawlers = [
        ("eastmoney", EastMoneyCrawler()),
        ("taoguba", TaogubaCrawler()),
        ("xueqiu", XueqiuCrawler()),
    ]

    async def _safe_fetch(name: str, crawler, codes: list[str], dt: date) -> list[dict]:
        try:
            return await crawler.fetch(codes, dt)
        except Exception:
            logger.warning("数据源 %s 采集失败，跳过", name, exc_info=True)
            return []

    tasks = [
        _safe_fetch(name, crawler, ts_codes, target_date)
        for name, crawler in crawlers
    ]

    results = await asyncio.gather(*tasks)

    all_news = []
    for items in results:
        all_news.extend(items)

    logger.info(
        "新闻采集汇总: %d 条（%d 只股票，%s）",
        len(all_news), len(ts_codes), target_date,
    )
    return all_news
