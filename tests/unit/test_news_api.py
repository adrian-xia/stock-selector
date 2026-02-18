"""新闻 API 端点测试（mock 数据库）。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

from app.api.news import (
    AnnouncementItem,
    NewsListResponse,
    SentimentTrendItem,
    SentimentSummaryItem,
    SentimentSummaryResponse,
)


class TestNewsListEndpoint:
    """GET /api/v1/news/list 测试。"""

    @pytest.mark.asyncio
    async def test_list_returns_paginated(self):
        """分页返回新闻列表。"""
        mock_rows = [
            MagicMock(
                id=1, ts_code="600519.SH", title="测试公告",
                summary="摘要", source="eastmoney", pub_date=date(2026, 2, 18),
                url="https://example.com", sentiment_score=0.5,
                sentiment_label="利好",
            ),
        ]
        mock_count = MagicMock()
        mock_count.scalar.return_value = 1

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count, mock_rows])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_news_list
            result = await get_news_list(page=1, page_size=20)

        assert isinstance(result, NewsListResponse)
        assert result.total == 1
        assert result.page == 1
        assert len(result.items) == 1
        assert result.items[0].ts_code == "600519.SH"

    @pytest.mark.asyncio
    async def test_list_with_filters(self):
        """带筛选条件查询。"""
        mock_count = MagicMock()
        mock_count.scalar.return_value = 0

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_count, []])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_news_list
            result = await get_news_list(
                page=1, page_size=20,
                ts_code="600519.SH", source="eastmoney",
                start_date=date(2026, 2, 1), end_date=date(2026, 2, 28),
            )

        assert result.total == 0
        assert result.items == []
        # 验证 execute 被调用了 2 次（count + data）
        assert mock_session.execute.call_count == 2


class TestSentimentTrendEndpoint:
    """GET /api/v1/news/sentiment-trend/{ts_code} 测试。"""

    @pytest.mark.asyncio
    async def test_trend_returns_data(self):
        """返回情感趋势数据（按日期升序）。"""
        mock_rows = [
            MagicMock(
                trade_date=date(2026, 2, 18), avg_sentiment=0.3,
                news_count=5, positive_count=3, negative_count=1, neutral_count=1,
            ),
            MagicMock(
                trade_date=date(2026, 2, 17), avg_sentiment=-0.1,
                news_count=3, positive_count=1, negative_count=1, neutral_count=1,
            ),
        ]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_rows)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_sentiment_trend
            result = await get_sentiment_trend(ts_code="600519.SH", days=30)

        assert len(result) == 2
        # 应按日期升序返回（reverse）
        assert result[0].trade_date == date(2026, 2, 17)
        assert result[1].trade_date == date(2026, 2, 18)

    @pytest.mark.asyncio
    async def test_trend_empty(self):
        """无数据返回空列表。"""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=[])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_sentiment_trend
            result = await get_sentiment_trend(ts_code="999999.SH", days=30)

        assert result == []


class TestSentimentSummaryEndpoint:
    """GET /api/v1/news/sentiment-summary 测试。"""

    @pytest.mark.asyncio
    async def test_summary_with_date(self):
        """指定日期返回摘要。"""
        mock_rows = [
            MagicMock(
                ts_code="600519.SH", avg_sentiment=0.5, news_count=10,
                positive_count=7, negative_count=1, neutral_count=2,
                source_breakdown={"eastmoney": 5, "xueqiu": 5},
            ),
        ]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_rows)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_sentiment_summary
            result = await get_sentiment_summary(
                trade_date=date(2026, 2, 18), top_n=20,
            )

        assert isinstance(result, SentimentSummaryResponse)
        assert result.trade_date == date(2026, 2, 18)
        assert len(result.items) == 1
        assert result.items[0].ts_code == "600519.SH"

    @pytest.mark.asyncio
    async def test_summary_no_date_uses_latest(self):
        """未指定日期时使用最新日期。"""
        mock_latest = MagicMock()
        mock_latest.scalar.return_value = date(2026, 2, 18)

        mock_rows = [
            MagicMock(
                ts_code="000001.SZ", avg_sentiment=-0.2, news_count=3,
                positive_count=0, negative_count=2, neutral_count=1,
                source_breakdown={"taoguba": 3},
            ),
        ]

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(side_effect=[mock_latest, mock_rows])
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_sentiment_summary
            result = await get_sentiment_summary(trade_date=None, top_n=20)

        assert result.trade_date == date(2026, 2, 18)
        assert len(result.items) == 1

    @pytest.mark.asyncio
    async def test_summary_no_data(self):
        """无数据时返回空。"""
        mock_latest = MagicMock()
        mock_latest.scalar.return_value = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock(return_value=mock_latest)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_factory = MagicMock(return_value=mock_session)

        with patch("app.api.news.async_session_factory", mock_factory):
            from app.api.news import get_sentiment_summary
            result = await get_sentiment_summary(trade_date=None, top_n=20)

        assert result.trade_date is None
        assert result.items == []
