"""新闻数据源采集模块。

提供东方财富、新浪 7x24 快讯、同花顺三个数据源的新闻采集能力。
"""

from app.data.sources.fetcher import fetch_all_news

__all__ = ["fetch_all_news"]
