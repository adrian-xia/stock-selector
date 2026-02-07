from datetime import date
from decimal import Decimal

from app.data.etl import clean_akshare_daily, clean_baostock_daily


class TestCleanBaostockDaily:
    def test_basic_cleaning(self):
        raw = [
            {
                "ts_code": "600519.SH",
                "trade_date": "2025-06-15",
                "open": Decimal("1700.00"),
                "high": Decimal("1720.00"),
                "low": Decimal("1690.00"),
                "close": Decimal("1710.00"),
                "pre_close": Decimal("1695.00"),
                "vol": Decimal("50000"),
                "amount": Decimal("8500000"),
                "turnover_rate": Decimal("0.35"),
                "pct_chg": Decimal("0.88"),
                "trade_status": "1",
            }
        ]
        result = clean_baostock_daily(raw)
        assert len(result) == 1
        r = result[0]
        assert r["ts_code"] == "600519.SH"
        assert r["trade_date"] == date(2025, 6, 15)
        assert r["open"] == Decimal("1700.00")
        assert r["data_source"] == "baostock"
        assert r["trade_status"] == "1"

    def test_zero_volume_marks_suspended(self):
        raw = [
            {
                "ts_code": "000001.SZ",
                "trade_date": "2025-06-15",
                "open": Decimal("10.00"),
                "high": Decimal("10.00"),
                "low": Decimal("10.00"),
                "close": Decimal("10.00"),
                "pre_close": None,
                "vol": Decimal("0"),
                "amount": Decimal("0"),
                "turnover_rate": None,
                "pct_chg": None,
                "trade_status": "1",
            }
        ]
        result = clean_baostock_daily(raw)
        assert result[0]["trade_status"] == "0"

    def test_skips_invalid_date(self):
        raw = [
            {
                "ts_code": "600519.SH",
                "trade_date": "invalid",
                "open": Decimal("100"),
                "high": Decimal("100"),
                "low": Decimal("100"),
                "close": Decimal("100"),
                "vol": Decimal("0"),
                "amount": Decimal("0"),
                "trade_status": "1",
            }
        ]
        result = clean_baostock_daily(raw)
        assert len(result) == 0

    def test_empty_input(self):
        assert clean_baostock_daily([]) == []


class TestCleanAkshareDaily:
    def test_basic_cleaning(self):
        raw = [
            {
                "ts_code": "600519.SH",
                "trade_date": "2025-06-15",
                "open": Decimal("1700.00"),
                "high": Decimal("1720.00"),
                "low": Decimal("1690.00"),
                "close": Decimal("1710.00"),
                "pre_close": None,
                "vol": Decimal("50000"),
                "amount": Decimal("8500000"),
                "turnover_rate": Decimal("0.35"),
                "pct_chg": Decimal("0.88"),
                "trade_status": "1",
            }
        ]
        result = clean_akshare_daily(raw)
        assert len(result) == 1
        assert result[0]["data_source"] == "akshare"
        assert result[0]["ts_code"] == "600519.SH"
