"""新闻情感分析器单元测试：mock Gemini 测试情感分析和每日聚合。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock


# ---------------------------------------------------------------------------
# aggregate_daily_sentiment 测试
# ---------------------------------------------------------------------------

class TestAggregateDailySentiment:
    """每日情感聚合测试。"""

    def test_basic_aggregation(self):
        """基本聚合：按股票分组计算平均分和正负中性计数。"""
        from app.ai.news_analyzer import aggregate_daily_sentiment

        announcements = [
            {"ts_code": "600519.SH", "sentiment_score": 0.5, "source": "eastmoney"},
            {"ts_code": "600519.SH", "sentiment_score": -0.3, "source": "ths"},
            {"ts_code": "600519.SH", "sentiment_score": 0.1, "source": "sina"},
            {"ts_code": "000001.SZ", "sentiment_score": 0.8, "source": "eastmoney"},
        ]

        result = aggregate_daily_sentiment(announcements, date(2026, 2, 18))

        assert len(result) == 2
        by_code = {r["ts_code"]: r for r in result}

        sh = by_code["600519.SH"]
        assert sh["news_count"] == 3
        assert sh["positive_count"] == 1  # 0.5 > 0.2
        assert sh["negative_count"] == 1  # -0.3 < -0.2
        assert sh["neutral_count"] == 1   # 0.1 in [-0.2, 0.2]
        assert abs(sh["avg_sentiment"] - 0.1) < 0.01

        sz = by_code["000001.SZ"]
        assert sz["news_count"] == 1
        assert sz["positive_count"] == 1

    def test_empty_input(self):
        """空输入返回空列表。"""
        from app.ai.news_analyzer import aggregate_daily_sentiment
        assert aggregate_daily_sentiment([], date(2026, 2, 18)) == []

    def test_source_breakdown(self):
        """来源统计正确。"""
        from app.ai.news_analyzer import aggregate_daily_sentiment

        announcements = [
            {"ts_code": "600519.SH", "sentiment_score": 0.5, "source": "eastmoney"},
            {"ts_code": "600519.SH", "sentiment_score": 0.3, "source": "eastmoney"},
            {"ts_code": "600519.SH", "sentiment_score": 0.1, "source": "ths"},
        ]

        result = aggregate_daily_sentiment(announcements, date(2026, 2, 18))
        assert result[0]["source_breakdown"] == {"eastmoney": 2, "ths": 1}

    def test_skip_none_ts_code(self):
        """跳过没有 ts_code 的记录。"""
        from app.ai.news_analyzer import aggregate_daily_sentiment

        announcements = [
            {"ts_code": "", "sentiment_score": 0.5, "source": "eastmoney"},
            {"ts_code": "600519.SH", "sentiment_score": 0.3, "source": "ths"},
        ]

        result = aggregate_daily_sentiment(announcements, date(2026, 2, 18))
        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"


# ---------------------------------------------------------------------------
# NewsSentimentAnalyzer 测试
# ---------------------------------------------------------------------------

class TestNewsSentimentAnalyzer:
    """情感分析器测试。"""

    @pytest.mark.asyncio
    async def test_analyze_empty_list(self):
        """空列表直接返回空。"""
        with patch("app.ai.news_analyzer.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_use_adc = False
            mock_settings.news_sentiment_batch_size = 10
            from app.ai.news_analyzer import NewsSentimentAnalyzer
            analyzer = NewsSentimentAnalyzer()
            result = await analyzer.analyze([])
        assert result == []

    @pytest.mark.asyncio
    async def test_analyze_without_ai(self):
        """AI 未启用时标记为中性。"""
        with patch("app.ai.news_analyzer.settings") as mock_settings:
            mock_settings.gemini_api_key = ""
            mock_settings.gemini_use_adc = False
            mock_settings.news_sentiment_batch_size = 10
            from app.ai.news_analyzer import NewsSentimentAnalyzer
            analyzer = NewsSentimentAnalyzer()
            items = [
                {"ts_code": "600519.SH", "title": "测试新闻", "summary": "摘要"},
            ]
            result = await analyzer.analyze(items)

        assert len(result) == 1
        assert result[0]["sentiment_score"] == 0.0
        assert result[0]["sentiment_label"] == "中性"

    @pytest.mark.asyncio
    async def test_analyze_with_ai_success(self):
        """AI 正常返回情感分析结果。"""
        mock_client = AsyncMock()
        mock_client.chat_json.return_value = [
            {
                "ts_code": "600519.SH",
                "title": "贵州茅台业绩大增",
                "sentiment_score": 0.85,
                "sentiment_label": "利好",
            }
        ]

        with patch("app.ai.news_analyzer.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_use_adc = False
            mock_settings.news_sentiment_batch_size = 10
            mock_settings.gemini_model_id = "gemini-2.0-flash"
            mock_settings.gemini_timeout = 30
            mock_settings.gemini_max_retries = 3
            mock_settings.gemini_gcp_project = ""
            mock_settings.gemini_gcp_location = ""
            mock_settings.gemini_max_tokens = 4096
            from app.ai.news_analyzer import NewsSentimentAnalyzer
            analyzer = NewsSentimentAnalyzer()
            analyzer._client = mock_client

            items = [
                {"ts_code": "600519.SH", "title": "贵州茅台业绩大增", "summary": "摘要"},
            ]
            result = await analyzer.analyze(items)

        assert len(result) == 1
        assert result[0]["sentiment_score"] == 0.85
        assert result[0]["sentiment_label"] == "利好"

    @pytest.mark.asyncio
    async def test_analyze_ai_failure_fallback(self):
        """AI 调用失败时降级为中性。"""
        mock_client = AsyncMock()
        mock_client.chat_json.side_effect = Exception("API error")

        with patch("app.ai.news_analyzer.settings") as mock_settings:
            mock_settings.gemini_api_key = "test-key"
            mock_settings.gemini_use_adc = False
            mock_settings.news_sentiment_batch_size = 10
            mock_settings.gemini_model_id = "gemini-2.0-flash"
            mock_settings.gemini_timeout = 30
            mock_settings.gemini_max_retries = 3
            mock_settings.gemini_gcp_project = ""
            mock_settings.gemini_gcp_location = ""
            mock_settings.gemini_max_tokens = 4096
            from app.ai.news_analyzer import NewsSentimentAnalyzer
            analyzer = NewsSentimentAnalyzer()
            analyzer._client = mock_client

            items = [
                {"ts_code": "600519.SH", "title": "测试", "summary": "摘要"},
            ]
            result = await analyzer.analyze(items)

        assert len(result) == 1
        assert result[0]["sentiment_score"] == 0.0
        assert result[0]["sentiment_label"] == "中性"
