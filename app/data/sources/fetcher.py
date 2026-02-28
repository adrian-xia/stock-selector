"""统一新闻采集入口：并行调用 3 个数据源。"""

import asyncio
import logging
from datetime import date

from sqlalchemy import select, text

from app.data.sources.eastmoney import EastMoneyCrawler
from app.data.sources.sina import SinaCrawler
from app.data.sources.ths import THSCrawler

logger = logging.getLogger(__name__)


async def _load_stock_names() -> dict[str, str]:
    """从 stocks 表加载 {ts_code: name} 映射，供新浪快讯文本匹配使用。

    失败时返回空 dict（降级为仅代码匹配）。
    """
    try:
        from app.database import async_session_factory
        async with async_session_factory() as session:
            result = await session.execute(text("SELECT ts_code, name FROM stocks"))
            return {row[0]: row[1] for row in result.fetchall()}
    except Exception:
        logger.warning("加载股票名称映射失败，降级为仅代码匹配", exc_info=True)
        return {}


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
    # 加载股票名称映射（供新浪快讯匹配）
    stock_names = await _load_stock_names()

    crawlers = [
        ("eastmoney", EastMoneyCrawler()),
        ("sina", SinaCrawler(stock_names=stock_names)),
        ("ths", THSCrawler()),
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
