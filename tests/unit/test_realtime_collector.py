"""测试实时行情采集器。"""

import asyncio
from datetime import datetime, time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.realtime.collector import RealtimeCollector, is_trading_hours


class TestIsTradingHours:
    """测试交易时段判断。"""

    def test_before_trading(self):
        dt = datetime(2026, 2, 19, 9, 0, 0)
        assert is_trading_hours(dt) is False

    def test_trading_start(self):
        dt = datetime(2026, 2, 19, 9, 15, 0)
        assert is_trading_hours(dt) is True

    def test_midday(self):
        dt = datetime(2026, 2, 19, 12, 0, 0)
        assert is_trading_hours(dt) is True

    def test_trading_end(self):
        dt = datetime(2026, 2, 19, 15, 0, 0)
        assert is_trading_hours(dt) is True

    def test_after_trading(self):
        dt = datetime(2026, 2, 19, 15, 1, 0)
        assert is_trading_hours(dt) is False


class TestRealtimeCollector:
    """测试 RealtimeCollector。"""

    def _make_collector(self):
        client = AsyncMock()
        publisher = AsyncMock()
        collector = RealtimeCollector(client, publisher)
        return collector, client, publisher

    def test_add_stock(self):
        collector, _, _ = self._make_collector()
        assert collector.add_stock("600519.SH") is True
        assert "600519.SH" in collector.watchlist

    def test_add_stock_limit(self):
        collector, _, _ = self._make_collector()
        with patch("app.realtime.collector.settings") as mock_settings:
            mock_settings.realtime_max_stocks = 2
            mock_settings.realtime_poll_interval = 3
            collector.add_stock("600519.SH")
            collector.add_stock("000001.SZ")
            assert collector.add_stock("600036.SH") is False

    def test_remove_stock(self):
        collector, _, _ = self._make_collector()
        collector.add_stock("600519.SH")
        collector.remove_stock("600519.SH")
        assert "600519.SH" not in collector.watchlist

    @pytest.mark.asyncio
    async def test_fetch_and_publish(self):
        """测试获取行情并发布。"""
        collector, client, publisher = self._make_collector()
        collector.add_stock("600519.SH")
        client.fetch_realtime_quote.return_value = [
            {"ts_code": "600519.SH", "close": 1800.0, "pct_chg": 1.5},
        ]
        await collector._fetch_and_publish()
        publisher.publish.assert_called_once_with(
            "600519.SH", {"ts_code": "600519.SH", "close": 1800.0, "pct_chg": 1.5}
        )

    @pytest.mark.asyncio
    async def test_fetch_fallback_to_daily(self):
        """测试 fetch_realtime_quote 不存在时回退到 daily。"""
        collector, client, publisher = self._make_collector()
        collector.add_stock("600519.SH")
        client.fetch_realtime_quote.side_effect = AttributeError
        client.fetch_raw_daily.return_value = [
            {"ts_code": "600519.SH", "close": 1800.0},
        ]
        await collector._fetch_and_publish()
        client.fetch_raw_daily.assert_called_once()
        publisher.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动和停止。"""
        collector, _, _ = self._make_collector()
        assert collector.is_running is False
        await collector.start()
        assert collector.is_running is True
        await collector.stop()
        assert collector.is_running is False
