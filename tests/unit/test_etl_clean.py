from datetime import date
from decimal import Decimal

from app.data.etl import (
    transform_tushare_daily,
    transform_tushare_stock_basic,
    transform_tushare_trade_cal,
)


class TestTransformTushareStockBasic:
    def test_basic_transform(self):
        raw = [
            {
                "ts_code": "600519.SH",
                "symbol": "600519",
                "name": "贵州茅台",
                "area": "贵州",
                "industry": "白酒",
                "market": "主板",
                "list_date": "20010827",
                "delist_date": None,
                "list_status": "L",
            }
        ]
        result = transform_tushare_stock_basic(raw)
        assert len(result) == 1
        r = result[0]
        assert r["ts_code"] == "600519.SH"
        assert r["name"] == "贵州茅台"
        assert r["list_date"] == date(2001, 8, 27)
        assert r["delist_date"] is None
        assert r["list_status"] == "L"

    def test_empty_input(self):
        assert transform_tushare_stock_basic([]) == []

    def test_skips_empty_ts_code(self):
        raw = [{"ts_code": "", "name": "test"}]
        assert transform_tushare_stock_basic(raw) == []


class TestTransformTushareTradeCal:
    def test_basic_transform(self):
        raw = [
            {"cal_date": "20260215", "is_open": 0, "exchange": "SSE", "pretrade_date": "20260213"},
            {"cal_date": "20260216", "is_open": 1, "exchange": "SSE", "pretrade_date": "20260215"},
        ]
        result = transform_tushare_trade_cal(raw)
        assert len(result) == 2
        assert result[0]["cal_date"] == date(2026, 2, 15)
        assert result[0]["is_open"] is False
        assert result[1]["is_open"] is True

    def test_empty_input(self):
        assert transform_tushare_trade_cal([]) == []


class TestTransformTushareDaily:
    def test_basic_transform_with_amount_conversion(self):
        """amount 千元 → 元转换"""
        raw_daily = [
            {
                "ts_code": "600519.SH",
                "trade_date": "20260214",
                "open": 1700.0,
                "high": 1720.0,
                "low": 1690.0,
                "close": 1710.0,
                "pre_close": 1695.0,
                "change": 15.0,
                "pct_chg": 0.88,
                "vol": 50000.0,
                "amount": 8500.0,  # 千元
            }
        ]
        raw_adj = [
            {"ts_code": "600519.SH", "trade_date": "20260214", "adj_factor": 108.031}
        ]
        raw_basic = [
            {"ts_code": "600519.SH", "trade_date": "20260214", "turnover_rate": 0.35}
        ]
        result = transform_tushare_daily(raw_daily, raw_adj, raw_basic)
        assert len(result) == 1
        r = result[0]
        assert r["ts_code"] == "600519.SH"
        assert r["trade_date"] == date(2026, 2, 14)
        assert r["amount"] == Decimal("8500000")  # 8500 * 1000
        assert r["adj_factor"] == Decimal("108.031")
        assert r["turnover_rate"] == Decimal("0.35")
        assert r["data_source"] == "tushare"
        assert r["trade_status"] == "1"

    def test_zero_volume_marks_suspended(self):
        raw_daily = [
            {
                "ts_code": "000001.SZ",
                "trade_date": "20260214",
                "open": 10.0, "high": 10.0, "low": 10.0, "close": 10.0,
                "pre_close": 10.0, "change": 0.0, "pct_chg": 0.0,
                "vol": 0.0, "amount": 0.0,
            }
        ]
        result = transform_tushare_daily(raw_daily, [], [])
        assert result[0]["trade_status"] == "0"

    def test_empty_input(self):
        assert transform_tushare_daily([], [], []) == []
