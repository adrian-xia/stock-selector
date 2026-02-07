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
