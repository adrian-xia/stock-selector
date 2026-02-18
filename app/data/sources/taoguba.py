"""淘股吧讨论热度采集。

通过淘股吧公开页面获取个股讨论数据。
"""

import asyncio
import logging
import re
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.taoguba.com.cn/quotes/{code}"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
}


def _ts_code_to_tgb_code(ts_code: str) -> str:
    """将 Tushare 代码转为淘股吧代码格式。"""
    return ts_code.split(".")[0]


class TaogubaCrawler:
    """淘股吧讨论热度采集器。"""

    def __init__(self, timeout: int | None = None, max_pages: int | None = None) -> None:
        self._timeout = timeout or settings.news_crawl_timeout
        self._max_pages = max_pages or settings.news_crawl_max_pages

    async def fetch(
        self,
        ts_codes: list[str],
        target_date: date,
    ) -> list[dict]:
        """采集指定股票在目标日期的讨论。

        Args:
            ts_codes: 股票代码列表
            target_date: 目标日期

        Returns:
            讨论字典列表
        """
        results: list[dict] = []

        async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
            for ts_code in ts_codes:
                try:
                    items = await self._fetch_stock(client, ts_code, target_date)
                    results.extend(items)
                except Exception:
                    logger.warning("淘股吧采集失败: %s", ts_code, exc_info=True)
                await asyncio.sleep(1.5)

        logger.info("淘股吧采集完成: %d 条讨论", len(results))
        return results

    async def _fetch_stock(
        self,
        client: httpx.AsyncClient,
        ts_code: str,
        target_date: date,
    ) -> list[dict]:
        """采集单只股票的讨论。"""
        code = _ts_code_to_tgb_code(ts_code)
        url = f"https://www.taoguba.com.cn/searchResult?kw={code}"
        items: list[dict] = []

        for attempt in range(3):
            try:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
                break
            except Exception:
                if attempt == 2:
                    return items
                await asyncio.sleep(1.0 * (attempt + 1))

        # 简单提取标题（从 HTML 中提取讨论标题）
        titles = re.findall(r'<a[^>]*class="[^"]*subject[^"]*"[^>]*>([^<]+)</a>', html)
        for title in titles[:10]:  # 最多取 10 条
            title = title.strip()
            if title:
                items.append({
                    "ts_code": ts_code,
                    "title": title,
                    "summary": title,
                    "pub_date": target_date,
                    "url": f"https://www.taoguba.com.cn/searchResult?kw={code}",
                    "source": "taoguba",
                })

        return items
