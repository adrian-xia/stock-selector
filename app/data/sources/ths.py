"""同花顺个股新闻采集。

通过同花顺公开 API 获取个股新闻标题和摘要，替代已失效的雪球数据源。
"""

import asyncio
import logging
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 同花顺个股新闻 API
_BASE_URL = "https://news.10jqka.com.cn/tapp/news/push/stock"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://news.10jqka.com.cn/",
}


def _ts_code_to_ths_code(ts_code: str) -> str:
    """将 Tushare 代码转为同花顺代码格式。

    600519.SH -> 600519（同花顺只需数字部分）
    """
    return ts_code.split(".")[0]


class THSCrawler:
    """同花顺个股新闻采集器。"""

    def __init__(self, timeout: int | None = None, max_pages: int | None = None) -> None:
        self._timeout = timeout or settings.news_crawl_timeout
        self._max_pages = max_pages or settings.news_crawl_max_pages

    async def fetch(
        self,
        ts_codes: list[str],
        target_date: date,
    ) -> list[dict]:
        """采集指定股票在目标日期的新闻。

        Args:
            ts_codes: 股票代码列表
            target_date: 目标日期

        Returns:
            新闻字典列表
        """
        results: list[dict] = []

        async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
            for ts_code in ts_codes:
                try:
                    items = await self._fetch_stock(client, ts_code, target_date)
                    results.extend(items)
                except Exception:
                    logger.warning("同花顺采集失败: %s", ts_code, exc_info=True)
                # 限流：请求间隔 1 秒
                await asyncio.sleep(1.0)

        logger.info("同花顺采集完成: %d 条新闻", len(results))
        return results

    async def _fetch_stock(
        self,
        client: httpx.AsyncClient,
        ts_code: str,
        target_date: date,
    ) -> list[dict]:
        """采集单只股票的新闻。"""
        ths_code = _ts_code_to_ths_code(ts_code)
        items: list[dict] = []
        date_str = target_date.strftime("%Y-%m-%d")

        for page in range(1, self._max_pages + 1):
            params = {
                "stockcode": ths_code,
                "page": str(page),
                "tag": "",
                "track": "stock",
            }

            for attempt in range(3):
                try:
                    resp = await client.get(_BASE_URL, params=params)
                    resp.raise_for_status()
                    data = resp.json()
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(1.0 * (attempt + 1))

            news_list = data.get("data", {}).get("list", [])
            if not news_list:
                break

            for news in news_list:
                title = news.get("title", "").strip()
                if not title:
                    continue
                items.append({
                    "ts_code": ts_code,
                    "title": title[:500],
                    "summary": news.get("digest", title)[:200],
                    "pub_date": date_str,
                    "url": news.get("url", ""),
                    "source": "ths",
                })

            # 不足一页说明没有更多数据
            if len(news_list) < 20:
                break

        return items
