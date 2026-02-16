from datetime import date
from decimal import Decimal

from app.data.etl import normalize_stock_code, parse_date, parse_decimal


class TestNormalizeStockCode:
    def test_baostock_sh(self):
        assert normalize_stock_code("sh.600519", "baostock") == "600519.SH"

    def test_baostock_sz(self):
        assert normalize_stock_code("sz.000001", "baostock") == "000001.SZ"

    def test_akshare_sh(self):
        assert normalize_stock_code("600519", "akshare") == "600519.SH"

    def test_akshare_sz(self):
        assert normalize_stock_code("000001", "akshare") == "000001.SZ"

    def test_akshare_gem(self):
        assert normalize_stock_code("300750", "akshare") == "300750.SZ"

    def test_akshare_bj(self):
        assert normalize_stock_code("830799", "akshare") == "830799.BJ"

    def test_akshare_bj_4xx(self):
        assert normalize_stock_code("430047", "akshare") == "430047.BJ"

    def test_empty_string(self):
        assert normalize_stock_code("", "baostock") == ""

    def test_already_standard(self):
        result = normalize_stock_code("600519.SH", "baostock")
        # Not a baostock format, returned as-is
        assert result == "600519.SH"


class TestParseDecimal:
    def test_valid_number(self):
        assert parse_decimal("1705.20") == Decimal("1705.20")

    def test_integer(self):
        assert parse_decimal("100") == Decimal("100")

    def test_negative(self):
        assert parse_decimal("-5.21") == Decimal("-5.21")

    def test_empty_string(self):
        assert parse_decimal("") is None

    def test_na(self):
        assert parse_decimal("N/A") is None

    def test_dash(self):
        assert parse_decimal("--") is None

    def test_none_string(self):
        assert parse_decimal("None") is None

    def test_none_value(self):
        assert parse_decimal(None) is None

    def test_float_nan(self):
        assert parse_decimal(float("nan")) is None

    def test_float_value(self):
        assert parse_decimal(3.14) == Decimal("3.14")

    def test_invalid_string(self):
        assert parse_decimal("error") is None


class TestParseDate:
    def test_hyphenated(self):
        assert parse_date("2025-01-15") == date(2025, 1, 15)

    def test_compact(self):
        assert parse_date("20250115") == date(2025, 1, 15)

    def test_empty(self):
        assert parse_date("") is None

    def test_none(self):
        assert parse_date(None) is None

    def test_na(self):
        assert parse_date("N/A") is None

    def test_invalid(self):
        assert parse_date("not-a-date") is None

    def test_invalid_compact(self):
        assert parse_date("2025130") is None


# ---------------------------------------------------------------------------
# P2 资金流向 ETL 测试
# ---------------------------------------------------------------------------


class TestTransformTushareMoneyflow:
    """transform_tushare_moneyflow 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_moneyflow

        raw = [{"ts_code": "600519.SH", "trade_date": "20260216",
                "buy_sm_vol": 100, "buy_sm_amount": 5000.0,
                "sell_sm_vol": 80, "sell_sm_amount": 4000.0,
                "buy_md_vol": None, "buy_md_amount": None,
                "sell_md_vol": 0, "sell_md_amount": 0,
                "buy_lg_vol": 50, "buy_lg_amount": 10000.0,
                "sell_lg_vol": 30, "sell_lg_amount": 6000.0,
                "buy_elg_vol": 10, "buy_elg_amount": 20000.0,
                "sell_elg_vol": 5, "sell_elg_amount": 10000.0,
                "net_mf_amount": 15000.0}]
        result = transform_tushare_moneyflow(raw)
        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["trade_date"] == date(2026, 2, 16)
        assert result[0]["data_source"] == "tushare"
        assert result[0]["buy_md_vol"] == Decimal("0")  # None → 0

    def test_empty(self):
        from app.data.etl import transform_tushare_moneyflow
        assert transform_tushare_moneyflow([]) == []

    def test_skip_empty_ts_code(self):
        from app.data.etl import transform_tushare_moneyflow

        raw = [{"ts_code": "", "trade_date": "20260216",
                "buy_sm_vol": 100, "buy_sm_amount": 5000.0,
                "sell_sm_vol": 0, "sell_sm_amount": 0,
                "buy_md_vol": 0, "buy_md_amount": 0,
                "sell_md_vol": 0, "sell_md_amount": 0,
                "buy_lg_vol": 0, "buy_lg_amount": 0,
                "sell_lg_vol": 0, "sell_lg_amount": 0,
                "buy_elg_vol": 0, "buy_elg_amount": 0,
                "sell_elg_vol": 0, "sell_elg_amount": 0,
                "net_mf_amount": 0}]
        assert transform_tushare_moneyflow(raw) == []


class TestTransformTushareTopList:
    """transform_tushare_top_list 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_top_list

        raw = [{"ts_code": "000001.SZ", "trade_date": "20260216",
                "name": "平安银行", "l_buy": 50000.0, "l_sell": 30000.0,
                "net_amount": 20000.0, "reason": "日涨幅偏离值达7%"}]
        result = transform_tushare_top_list(raw)
        assert len(result) == 1
        assert result[0]["buy_total"] == Decimal("50000.0")
        assert result[0]["sell_total"] == Decimal("30000.0")
        assert result[0]["net_buy"] == Decimal("20000.0")
        assert result[0]["reason"] == "日涨幅偏离值达7%"
        assert result[0]["data_source"] == "tushare"

    def test_empty(self):
        from app.data.etl import transform_tushare_top_list
        assert transform_tushare_top_list([]) == []
