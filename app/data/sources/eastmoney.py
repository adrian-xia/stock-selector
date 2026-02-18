"""东方财富公告采集。

通过东方财富公开 API 获取上市公司公告标题和摘要。
"""

import asyncio
import logging
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# 东方财富公告搜索 API
_BASE_URL = "https://np-anotice-stock.eastmoney.com/api/security/ann"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Referer": "https://data.eastmoney.com/",
}


def _ts_code_to_em_code(ts_code: str) -> str:
    """将 Tushare 代码转为东方财富代码格式。

    600519.SH -> 600519（东方财富只需数字部分）
    """
    return ts_code.split(".")[0]


class EastMoneyCrawler:
    """东方财富公告采集器。"""

    def __init__(self, timeout: int | None = None, max_pages: int | None = None) -> None:
        self._timeout = timeout or settings.news_crawl_timeout
        self._max_pages = max_pages or settings.news_crawl_max_pages

    async def fetch(
        self,
        ts_codes: list[str],
        target_date: date,
    ) -> list[dict]:
        """采集指定股票在目标日期的公告。

        Args:
            ts_codes: 股票代码列表
            target_date: 目标日期

        Returns:
            公告字典列表
        """
        results: list[dict] = []
        date_str = target_date.strftime("%Y-%m-%d")

        async with httpx.AsyncClient(timeout=self._timeout, headers=_HEADERS) as client:
            for ts_code in ts_codes:
                try:
                    items = await self._fetch_stock(client, ts_code, date_str)
                    results.extend(items)
                except Exception:
                    logger.warning("东方财富采集失败: %s", ts_code, exc_info=True)
                # 限流：请求间隔 1 秒
                await asyncio.sleep(1.0)

        logger.info("东方财富采集完成: %d 条公告", len(results))
        return results

    async def _fetch_stock(
        self,
        client: httpx.AsyncClient,
        ts_code: str,
        date_str: str,
    ) -> list[dict]:
        """采集单只股票的公告。"""
        em_code = _ts_code_to_em_code(ts_code)
        items: list[dict] = []

        for page in range(1, self._max_pages + 1):
            params = {
                "sr": "-1",
                "page_size": "30",
                "page_index": str(page),
                "ann_type": "SHA,SZA",
                "stock_list": em_code,
                "begin_time": date_str,
                "end_time": date_str,
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

            ann_list = data.get("data", {}).get("list", [])
            if not ann_list:
                break

            for ann in ann_list:
                items.append({
                    "ts_code": ts_code,
                    "title": ann.get("title", "").strip(),
                    "summary": ann.get("title", "").strip(),  # 东方财富公告无摘要，用标题
                    "pub_date": date_str,
                    "url": f"https://data.eastmoney.com/notices/detail/{em_code}/{ann.get('art_code', '')}.html",
                    "source": "eastmoney",
                })

            # 不足一页说明没有更多数据
            if len(ann_list) < 30:
                break

        return items
