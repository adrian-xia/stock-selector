"""雪球讨论热度采集。

通过雪球公开 API 获取个股讨论数据。
"""

import asyncio
import logging
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_BASE_URL = "https://xueqiu.com/query/v1/symbol/search/status"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Origin": "https://xueqiu.com",
}
# 雪球需要先访问首页获取 cookie
_HOME_URL = "https://xueqiu.com/"


def _ts_code_to_xq_code(ts_code: str) -> str:
    """将 Tushare 代码转为雪球代码格式。

    600519.SH -> SH600519
    000001.SZ -> SZ000001
    """
    parts = ts_code.split(".")
    if len(parts) == 2:
        return f"{parts[1]}{parts[0]}"
    return ts_code


class XueqiuCrawler:
    """雪球讨论热度采集器。"""

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

        async with httpx.AsyncClient(
            timeout=self._timeout, headers=_HEADERS, follow_redirects=True,
        ) as client:
            # 先访问首页获取 cookie
            try:
                await client.get(_HOME_URL)
            except Exception:
                logger.warning("雪球首页访问失败，跳过 cookie 获取")

            for ts_code in ts_codes:
                try:
                    items = await self._fetch_stock(client, ts_code, target_date)
                    results.extend(items)
                except Exception:
                    logger.warning("雪球采集失败: %s", ts_code, exc_info=True)
                await asyncio.sleep(1.5)

        logger.info("雪球采集完成: %d 条讨论", len(results))
        return results

    async def _fetch_stock(
        self,
        client: httpx.AsyncClient,
        ts_code: str,
        target_date: date,
    ) -> list[dict]:
        """采集单只股票的讨论。"""
        xq_code = _ts_code_to_xq_code(ts_code)
        items: list[dict] = []

        params = {
            "count": "10",
            "comment": "0",
            "symbol": xq_code,
            "hl": "0",
            "source": "all",
            "sort": "time",
            "page": "1",
            "q": "",
        }

        for attempt in range(3):
            try:
                resp = await client.get(_BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception:
                if attempt == 2:
                    return items
                await asyncio.sleep(1.0 * (attempt + 1))

        statuses = data.get("list", [])
        for status in statuses[:10]:
            title = status.get("title") or status.get("description", "")
            # 清理 HTML 标签
            import re
            title = re.sub(r"<[^>]+>", "", title).strip()
            if not title:
                continue

            summary = status.get("description", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:200]

            items.append({
                "ts_code": ts_code,
                "title": title[:500],
                "summary": summary or title[:200],
                "pub_date": target_date,
                "url": f"https://xueqiu.com/S/{xq_code}",
                "source": "xueqiu",
            })

        return items
