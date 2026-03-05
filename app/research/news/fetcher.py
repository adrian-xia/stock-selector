"""新闻抓取器：抽象 NewsSource 接口 + Sina 实现。

设计原则：
- NewsSource 定义统一的 fetch_macro() 接口
- 返回标准化的 RawNewsItem 列表
- 不做个股匹配（与现有 SinaCrawler.fetch 的区别）
"""

import asyncio
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# HTML 标签清理正则
_HTML_RE = re.compile(r"<[^>]+>")


@dataclass
class RawNewsItem:
    """标准化的原始新闻条目。"""

    title: str
    content: str
    pub_time: datetime
    source: str  # sina / tushare / cls
    url: str = ""
    tags: list[str] = field(default_factory=list)


class NewsSource(ABC):
    """新闻数据源抽象接口。"""

    @abstractmethod
    async def fetch_macro(self, target_date: date, max_items: int = 100) -> list[RawNewsItem]:
        """获取宏观/全市场新闻。

        Args:
            target_date: 目标日期
            max_items: 最大返回条数

        Returns:
            标准化的新闻条目列表
        """
        ...


class SinaMacroSource(NewsSource):
    """新浪 7x24 快讯宏观新闻源。

    复用已验证的 API（Phase 0 PoC 确认 60% 宏观覆盖率）。
    与 app/data/sources/sina.py 的 SinaCrawler 区别：
    - 不做 per-stock 文本匹配
    - 直接返回全量快讯
    """

    BASE_URL = "https://zhibo.sina.com.cn/api/zhibo/feed"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
        "Referer": "https://finance.sina.com.cn/",
    }

    def __init__(self, timeout: int = 15, max_pages: int = 5) -> None:
        self._timeout = timeout
        self._max_pages = max_pages

    async def fetch_macro(self, target_date: date, max_items: int = 100) -> list[RawNewsItem]:
        """拉取新浪 7x24 快讯流，返回标准化新闻。"""
        results: list[RawNewsItem] = []

        async with httpx.AsyncClient(timeout=self._timeout, headers=self.HEADERS) as client:
            for page in range(1, self._max_pages + 1):
                if len(results) >= max_items:
                    break

                try:
                    items = await self._fetch_page(client, page)
                except Exception:
                    logger.warning("新浪快讯第 %d 页采集失败", page, exc_info=True)
                    break

                if not items:
                    break

                for item in items:
                    text = _HTML_RE.sub("", item.get("rich_text", "")).strip()
                    if not text or len(text) < 10:
                        continue

                    # 解析时间
                    create_time = item.get("create_time", "")
                    try:
                        pub_time = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
                    except (ValueError, TypeError):
                        pub_time = datetime.combine(target_date, datetime.min.time())

                    # 仅保留目标日期的新闻
                    if pub_time.date() != target_date:
                        continue

                    # 提取标签
                    tags = []
                    tag_data = item.get("tag", [])
                    if isinstance(tag_data, list):
                        tags = [t.get("name", "") for t in tag_data if isinstance(t, dict) and t.get("name")]

                    results.append(RawNewsItem(
                        title=text[:200],
                        content=text,
                        pub_time=pub_time,
                        source="sina",
                        url="",
                        tags=tags,
                    ))

                await asyncio.sleep(0.5)  # 限流

        logger.info("新浪宏观新闻采集完成: %d 条", len(results))
        return results[:max_items]

    async def _fetch_page(self, client: httpx.AsyncClient, page: int) -> list[dict]:
        """拉取单页快讯数据。"""
        params = {"page": str(page), "page_size": "20", "zhibo_id": "152"}

        for attempt in range(3):
            try:
                resp = await client.get(self.BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
                return data.get("result", {}).get("data", {}).get("feed", {}).get("list", [])
            except Exception:
                if attempt == 2:
                    raise
                await asyncio.sleep(1.0 * (attempt + 1))
        return []


async def fetch_macro_news(target_date: date, max_items: int = 100) -> list[RawNewsItem]:
    """便捷入口：使用默认数据源获取宏观新闻。"""
    source = SinaMacroSource(
        timeout=settings.news_crawl_timeout,
        max_pages=settings.news_crawl_max_pages,
    )
    return await source.fetch_macro(target_date, max_items)
