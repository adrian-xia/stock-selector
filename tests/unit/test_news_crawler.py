"""新闻爬虫单元测试：mock HTTP 请求测试 3 个数据源。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch, MagicMock

import httpx


# ---------------------------------------------------------------------------
# EastMoneyCrawler 测试
# ---------------------------------------------------------------------------

class TestEastMoneyCrawler:
    """东方财富爬虫测试。"""

    @pytest.fixture
    def crawler(self):
        with patch("app.data.sources.eastmoney.settings") as mock_settings:
            mock_settings.news_crawl_timeout = 10
            mock_settings.news_crawl_max_pages = 2
            from app.data.sources.eastmoney import EastMoneyCrawler
            return EastMoneyCrawler(timeout=10, max_pages=2)

    @pytest.mark.asyncio
    async def test_fetch_returns_announcements(self, crawler):
        """正常返回公告列表。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "list": [
                    {"title": "关于2025年年度报告的公告", "art_code": "AN202602181234"},
                    {"title": "关于股东减持计划的公告", "art_code": "AN202602181235"},
                ]
            }
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 2
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["source"] == "eastmoney"
        assert "年度报告" in result[0]["title"]

    @pytest.mark.asyncio
    async def test_fetch_empty_response(self, crawler):
        """API 返回空列表。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"data": {"list": []}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_handles_error(self, crawler):
        """单只股票采集失败不影响其他。"""
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.raise_for_status = MagicMock()
        mock_response_ok.json.return_value = {
            "data": {"list": [{"title": "测试公告", "art_code": "AN001"}]}
        }

        call_count = 0
        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 3:  # 第一只股票 3 次重试都失败
                raise httpx.HTTPError("timeout")
            return mock_response_ok

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=side_effect)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["000001.SZ", "600519.SH"], date(2026, 2, 18))

        # 第一只失败（3次重试耗尽），第二只成功（call_count=4 返回 ok）
        assert any(r["ts_code"] == "600519.SH" for r in result)
        assert not any(r["ts_code"] == "000001.SZ" for r in result)


class TestEastMoneyCodeConvert:
    """东方财富代码转换测试。"""

    def test_sh_code(self):
        from app.data.sources.eastmoney import _ts_code_to_em_code
        assert _ts_code_to_em_code("600519.SH") == "600519"

    def test_sz_code(self):
        from app.data.sources.eastmoney import _ts_code_to_em_code
        assert _ts_code_to_em_code("000001.SZ") == "000001"


# ---------------------------------------------------------------------------
# TaogubaCrawler 测试
# ---------------------------------------------------------------------------

class TestTaogubaCrawler:
    """淘股吧爬虫测试。"""

    @pytest.fixture
    def crawler(self):
        with patch("app.data.sources.taoguba.settings") as mock_settings:
            mock_settings.news_crawl_timeout = 10
            mock_settings.news_crawl_max_pages = 2
            from app.data.sources.taoguba import TaogubaCrawler
            return TaogubaCrawler(timeout=10, max_pages=2)

    @pytest.mark.asyncio
    async def test_fetch_parses_html(self, crawler):
        """从 HTML 中提取讨论标题。"""
        html = '''
        <a class="subject" href="/topic/1">贵州茅台业绩大增</a>
        <a class="subject-link" href="/topic/2">茅台股价分析</a>
        '''
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.text = html

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        for item in result:
            assert item["source"] == "taoguba"
            assert item["ts_code"] == "600519.SH"

class TestTaogubaCodeConvert:
    """淘股吧代码转换测试。"""

    def test_convert(self):
        from app.data.sources.taoguba import _ts_code_to_tgb_code
        assert _ts_code_to_tgb_code("600519.SH") == "600519"


# ---------------------------------------------------------------------------
# XueqiuCrawler 测试
# ---------------------------------------------------------------------------

class TestXueqiuCrawler:
    """雪球爬虫测试。"""

    @pytest.fixture
    def crawler(self):
        with patch("app.data.sources.xueqiu.settings") as mock_settings:
            mock_settings.news_crawl_timeout = 10
            mock_settings.news_crawl_max_pages = 2
            from app.data.sources.xueqiu import XueqiuCrawler
            return XueqiuCrawler(timeout=10, max_pages=2)

    @pytest.mark.asyncio
    async def test_fetch_returns_discussions(self, crawler):
        """正常返回讨论列表。"""
        mock_home = MagicMock()
        mock_home.status_code = 200

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "list": [
                {"title": "茅台分析", "description": "<p>详细分析内容</p>"},
                {"title": "", "description": "<b>另一条讨论</b>"},
            ]
        }

        async def get_side_effect(url, **kwargs):
            if "xueqiu.com/" == url or url.endswith("xueqiu.com/"):
                return mock_home
            return mock_response

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=get_side_effect)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 2
        assert result[0]["source"] == "xueqiu"
        assert result[0]["ts_code"] == "600519.SH"


class TestXueqiuCodeConvert:
    """雪球代码转换测试。"""

    def test_sh_code(self):
        from app.data.sources.xueqiu import _ts_code_to_xq_code
        assert _ts_code_to_xq_code("600519.SH") == "SH600519"

    def test_sz_code(self):
        from app.data.sources.xueqiu import _ts_code_to_xq_code
        assert _ts_code_to_xq_code("000001.SZ") == "SZ000001"


# ---------------------------------------------------------------------------
# fetch_all_news 测试
# ---------------------------------------------------------------------------

class TestFetchAllNews:
    """统一采集入口测试。"""

    @pytest.mark.asyncio
    async def test_merges_all_sources(self):
        """合并 3 个数据源的结果。"""
        with (
            patch("app.data.sources.fetcher.EastMoneyCrawler") as em,
            patch("app.data.sources.fetcher.TaogubaCrawler") as tgb,
            patch("app.data.sources.fetcher.XueqiuCrawler") as xq,
        ):
            em_inst = AsyncMock()
            em_inst.fetch.return_value = [{"title": "em1", "source": "eastmoney"}]
            em.return_value = em_inst

            tgb_inst = AsyncMock()
            tgb_inst.fetch.return_value = [{"title": "tgb1", "source": "taoguba"}]
            tgb.return_value = tgb_inst

            xq_inst = AsyncMock()
            xq_inst.fetch.return_value = [{"title": "xq1", "source": "xueqiu"}]
            xq.return_value = xq_inst

            from app.data.sources.fetcher import fetch_all_news
            result = await fetch_all_news(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 3
        sources = {r["source"] for r in result}
        assert sources == {"eastmoney", "taoguba", "xueqiu"}

    @pytest.mark.asyncio
    async def test_one_source_failure(self):
        """单个数据源失败不影响其他。"""
        with (
            patch("app.data.sources.fetcher.EastMoneyCrawler") as em,
            patch("app.data.sources.fetcher.TaogubaCrawler") as tgb,
            patch("app.data.sources.fetcher.XueqiuCrawler") as xq,
        ):
            em_inst = AsyncMock()
            em_inst.fetch.side_effect = Exception("network error")
            em.return_value = em_inst

            tgb_inst = AsyncMock()
            tgb_inst.fetch.return_value = [{"title": "tgb1"}]
            tgb.return_value = tgb_inst

            xq_inst = AsyncMock()
            xq_inst.fetch.return_value = [{"title": "xq1"}]
            xq.return_value = xq_inst

            from app.data.sources.fetcher import fetch_all_news
            result = await fetch_all_news(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 2
