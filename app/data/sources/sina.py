"""新浪 7x24 快讯采集。

通过新浪财经 7x24 快讯流获取全市场新闻，本地文本匹配关联到个股。
替代已失效的淘股吧数据源。
"""

import asyncio
import logging
import re
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 新浪 7x24 快讯 API
_BASE_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://finance.sina.com.cn/",
}

# HTML 标签清理正则
_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _match_stocks(
    text: str,
    ts_codes: list[str],
    stock_names: dict[str, str],
) -> list[str]:
    """在文本中匹配股票代码或名称，返回匹配到的 ts_code 列表。

    匹配规则：
    - 6 位股票代码（如 600519）
    - 股票名称（≥2 字，如 贵州茅台）

    Args:
        text: 快讯文本
        ts_codes: 股票代码列表
        stock_names: {ts_code: name} 映射

    Returns:
        匹配到的 ts_code 列表（去重）
    """
    matched: list[str] = []
    for ts_code in ts_codes:
        code_num = ts_code.split(".")[0]
        # 按代码匹配
        if code_num in text:
            matched.append(ts_code)
            continue
        # 按名称匹配（名称至少 2 个字符）
        name = stock_names.get(ts_code, "")
        if len(name) >= 2 and name in text:
            matched.append(ts_code)
    return matched


class SinaCrawler:
    """新浪 7x24 快讯采集器。

    与其他爬虫的关键区别：全市场快讯流，需本地文本匹配关联到个股。
    """

    def __init__(
        self,
        stock_names: dict[str, str] | None = None,
        timeout: int | None = None,
        max_pages: int | None = None,
    ) -> None:
        self._stock_names = stock_names or {}
        self._timeout = timeout or settings.news_crawl_timeout
        self._max_pages = max_pages or settings.news_crawl_max_pages

    async def fetch(
        self,
        ts_codes: list[str],
        target_date: date,
    ) -> list[dict]:
        """拉取快讯流并匹配到指定股票。

        Args:
            ts_codes: 股票代码列表
            target_date: 目标日期

        Returns:
            匹配到的新闻字典列表
        """
        results: list[dict] = []
        date_str = target_date.strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
            for page in range(1, self._max_pages + 1):
                try:
                    feed_items = await self._fetch_page(client, page)
                except Exception:
                    logger.warning("新浪快讯第 %d 页采集失败", page, exc_info=True)
                    break

                if not feed_items:
                    break

                # 逐条匹配股票
                for item in feed_items:
                    text = _HTML_TAG_RE.sub("", item.get("rich_text", ""))
                    if not text.strip():
                        continue

                    matched_codes = _match_stocks(text, ts_codes, self._stock_names)
                    for ts_code in matched_codes:
                        results.append({
                            "ts_code": ts_code,
                            "title": text.strip()[:500],
                            "summary": text.strip()[:200],
                            "pub_date": date_str,
                            "url": "",
                            "source": "sina",
                        })

                # 限流
                await asyncio.sleep(1.0)

        logger.info("新浪快讯采集完成: %d 条匹配新闻", len(results))
        return results

    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> list[dict]:
        """拉取单页快讯。"""
        params = {
            "page": str(page),
            "page_size": "20",
            "zhibo_id": "152",
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

        return data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
