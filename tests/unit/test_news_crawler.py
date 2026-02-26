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
# THSCrawler 测试
# ---------------------------------------------------------------------------

class TestTHSCrawler:
    """同花顺爬虫测试。"""

    @pytest.fixture
    def crawler(self):
        with patch("app.data.sources.ths.settings") as mock_settings:
            mock_settings.news_crawl_timeout = 10
            mock_settings.news_crawl_max_pages = 2
            from app.data.sources.ths import THSCrawler
            return THSCrawler(timeout=10, max_pages=2)

    @pytest.mark.asyncio
    async def test_fetch_returns_news(self, crawler):
        """正常返回新闻列表。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "list": [
                    {"title": "贵州茅台发布年报", "digest": "业绩大增", "url": "https://news.10jqka.com.cn/1"},
                    {"title": "茅台股价创新高", "digest": "涨停分析", "url": "https://news.10jqka.com.cn/2"},
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
        assert result[0]["source"] == "ths"
        assert "年报" in result[0]["title"]

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
        """采集失败时优雅降级。"""
        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=httpx.HTTPError("timeout"))
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert result == []


class TestTHSCodeConvert:
    """同花顺代码转换测试。"""

    def test_sh_code(self):
        from app.data.sources.ths import _ts_code_to_ths_code
        assert _ts_code_to_ths_code("600519.SH") == "600519"

    def test_sz_code(self):
        from app.data.sources.ths import _ts_code_to_ths_code
        assert _ts_code_to_ths_code("000001.SZ") == "000001"


# ---------------------------------------------------------------------------
# SinaCrawler 测试
# ---------------------------------------------------------------------------

class TestSinaCrawler:
    """新浪快讯爬虫测试。"""

    @pytest.fixture
    def crawler(self):
        with patch("app.data.sources.sina.settings") as mock_settings:
            mock_settings.news_crawl_timeout = 10
            mock_settings.news_crawl_max_pages = 2
            from app.data.sources.sina import SinaCrawler
            return SinaCrawler(
                stock_names={"600519.SH": "贵州茅台", "000001.SZ": "平安银行"},
                timeout=10, max_pages=2,
            )

    @pytest.mark.asyncio
    async def test_fetch_match_by_code(self, crawler):
        """按股票代码匹配快讯。"""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.raise_for_status = MagicMock()
        resp_page1.json.return_value = {
            "result": {"data": {"feed": {"list": [
                {"rich_text": "<p>600519今日涨停，成交额超百亿</p>"},
            ]}}}
        }
        resp_empty = MagicMock()
        resp_empty.status_code = 200
        resp_empty.raise_for_status = MagicMock()
        resp_empty.json.return_value = {"result": {"data": {"feed": {"list": []}}}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=[resp_page1, resp_empty])
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["source"] == "sina"
        assert "涨停" in result[0]["title"]

    @pytest.mark.asyncio
    async def test_fetch_match_by_name(self, crawler):
        """按股票名称匹配快讯。"""
        resp_page1 = MagicMock()
        resp_page1.status_code = 200
        resp_page1.raise_for_status = MagicMock()
        resp_page1.json.return_value = {
            "result": {"data": {"feed": {"list": [
                {"rich_text": "贵州茅台发布年报，业绩大增"},
            ]}}}
        }
        resp_empty = MagicMock()
        resp_empty.status_code = 200
        resp_empty.raise_for_status = MagicMock()
        resp_empty.json.return_value = {"result": {"data": {"feed": {"list": []}}}}

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=[resp_page1, resp_empty])
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"

    @pytest.mark.asyncio
    async def test_fetch_no_match(self, crawler):
        """快讯与目标股票无关时返回空。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": {"data": {"feed": {"list": [
                {"rich_text": "央行今日开展逆回购操作"},
            ]}}}
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_empty_feed(self, crawler):
        """快讯流为空。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "result": {"data": {"feed": {"list": []}}}
        }

        with patch("httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            result = await crawler.fetch(["600519.SH"], date(2026, 2, 18))

        assert result == []


class TestSinaMatchStocks:
    """新浪快讯股票匹配逻辑测试。"""

    def test_match_by_code(self):
        from app.data.sources.sina import _match_stocks
        result = _match_stocks(
            "600519今日涨停",
            ["600519.SH", "000001.SZ"],
            {"600519.SH": "贵州茅台", "000001.SZ": "平安银行"},
        )
        assert result == ["600519.SH"]

    def test_match_by_name(self):
        from app.data.sources.sina import _match_stocks
        result = _match_stocks(
            "贵州茅台发布年报",
            ["600519.SH", "000001.SZ"],
            {"600519.SH": "贵州茅台", "000001.SZ": "平安银行"},
        )
        assert result == ["600519.SH"]

    def test_match_multiple(self):
        from app.data.sources.sina import _match_stocks
        result = _match_stocks(
            "贵州茅台和平安银行同时涨停",
            ["600519.SH", "000001.SZ"],
            {"600519.SH": "贵州茅台", "000001.SZ": "平安银行"},
        )
        assert set(result) == {"600519.SH", "000001.SZ"}

    def test_no_match(self):
        from app.data.sources.sina import _match_stocks
        result = _match_stocks(
            "央行今日开展逆回购操作",
            ["600519.SH"],
            {"600519.SH": "贵州茅台"},
        )
        assert result == []

    def test_empty_stock_names(self):
        """stock_names 为空时仅按代码匹配。"""
        from app.data.sources.sina import _match_stocks
        result = _match_stocks("600519涨停", ["600519.SH"], {})
        assert result == ["600519.SH"]


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
            patch("app.data.sources.fetcher.SinaCrawler") as sina,
            patch("app.data.sources.fetcher.THSCrawler") as ths,
            patch("app.data.sources.fetcher._load_stock_names", return_value={}),
        ):
            em_inst = AsyncMock()
            em_inst.fetch.return_value = [{"title": "em1", "source": "eastmoney"}]
            em.return_value = em_inst

            sina_inst = AsyncMock()
            sina_inst.fetch.return_value = [{"title": "sina1", "source": "sina"}]
            sina.return_value = sina_inst

            ths_inst = AsyncMock()
            ths_inst.fetch.return_value = [{"title": "ths1", "source": "ths"}]
            ths.return_value = ths_inst

            from app.data.sources.fetcher import fetch_all_news
            result = await fetch_all_news(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 3
        sources = {r["source"] for r in result}
        assert sources == {"eastmoney", "sina", "ths"}

    @pytest.mark.asyncio
    async def test_one_source_failure(self):
        """单个数据源失败不影响其他。"""
        with (
            patch("app.data.sources.fetcher.EastMoneyCrawler") as em,
            patch("app.data.sources.fetcher.SinaCrawler") as sina,
            patch("app.data.sources.fetcher.THSCrawler") as ths,
            patch("app.data.sources.fetcher._load_stock_names", return_value={}),
        ):
            em_inst = AsyncMock()
            em_inst.fetch.side_effect = Exception("network error")
            em.return_value = em_inst

            sina_inst = AsyncMock()
            sina_inst.fetch.return_value = [{"title": "sina1"}]
            sina.return_value = sina_inst

            ths_inst = AsyncMock()
            ths_inst.fetch.return_value = [{"title": "ths1"}]
            ths.return_value = ths_inst

            from app.data.sources.fetcher import fetch_all_news
            result = await fetch_all_news(["600519.SH"], date(2026, 2, 18))

        assert len(result) == 2
