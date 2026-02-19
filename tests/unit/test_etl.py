from datetime import date
from decimal import Decimal

from app.data.etl import normalize_stock_code, parse_date, parse_decimal


class TestNormalizeStockCode:
    def test_tushare_passthrough(self):
        """Tushare 格式直接透传。"""
        assert normalize_stock_code("600519.SH") == "600519.SH"

    def test_tushare_sz(self):
        assert normalize_stock_code("000001.SZ") == "000001.SZ"

    def test_empty_string(self):
        assert normalize_stock_code("") == ""

    def test_already_standard(self):
        result = normalize_stock_code("600519.SH", "tushare")
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


class TestTransformTushareIndexDaily:
    """transform_tushare_index_daily 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_index_daily

        raw = [{"ts_code": "000001.SH", "trade_date": "20260217",
                "open": 3200.5, "high": 3250.0, "low": 3180.0,
                "close": 3240.0, "pre_close": 3200.0,
                "change": 40.0, "pct_chg": 1.25,
                "vol": 300000000.0, "amount": 350000000.0}]
        result = transform_tushare_index_daily(raw)
        assert len(result) == 1
        assert result[0]["ts_code"] == "000001.SH"
        assert result[0]["trade_date"] == date(2026, 2, 17)
        assert result[0]["close"] == Decimal("3240.0")
        assert result[0]["vol"] == Decimal("300000000.0")

    def test_empty(self):
        from app.data.etl import transform_tushare_index_daily
        assert transform_tushare_index_daily([]) == []


class TestTransformTushareIndexWeight:
    """transform_tushare_index_weight 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_index_weight

        raw = [{"index_code": "000300.SH", "con_code": "600519.SH",
                "trade_date": "20260217", "weight": 3.52}]
        result = transform_tushare_index_weight(raw)
        assert len(result) == 1
        assert result[0]["index_code"] == "000300.SH"
        assert result[0]["con_code"] == "600519.SH"
        assert result[0]["trade_date"] == date(2026, 2, 17)
        assert result[0]["weight"] == Decimal("3.52")

    def test_empty(self):
        from app.data.etl import transform_tushare_index_weight
        assert transform_tushare_index_weight([]) == []


class TestTransformTushareIndexBasic:
    """transform_tushare_index_basic 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_index_basic

        raw = [{"ts_code": "000001.SH", "name": "上证综指",
                "fullname": "上证综合指数", "market": "SSE",
                "publisher": "上交所", "index_type": "综合指数",
                "category": "综合", "base_date": "19901219",
                "base_point": 100.0, "list_date": "19910715",
                "weight_rule": "总市值加权", "desc": None, "exp_date": None}]
        result = transform_tushare_index_basic(raw)
        assert len(result) == 1
        assert result[0]["ts_code"] == "000001.SH"
        assert result[0]["name"] == "上证综指"
        assert result[0]["base_date"] == date(1990, 12, 19)
        assert result[0]["base_point"] == Decimal("100.0")

    def test_empty(self):
        from app.data.etl import transform_tushare_index_basic
        assert transform_tushare_index_basic([]) == []


class TestTransformTushareIndexTechnical:
    """transform_tushare_index_technical 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_index_technical

        raw = [{"ts_code": "000001.SH", "trade_date": "20260217",
                "ma5": 3200.0, "ma10": 3180.0, "ma20": 3150.0,
                "ma60": 3100.0, "ma120": 3050.0, "ma250": 3000.0,
                "macd_dif": 15.5, "macd_dea": 12.3, "macd": 6.4,
                "kdj_k": 75.0, "kdj_d": 68.0, "kdj_j": 89.0,
                "rsi6": 62.0, "rsi12": 58.0, "rsi24": 55.0,
                "boll_upper": 3300.0, "boll_mid": 3200.0, "boll_lower": 3100.0,
                "atr": 45.0, "cci": 120.0, "wr": -25.0}]
        result = transform_tushare_index_technical(raw)
        assert len(result) == 1
        assert result[0]["ts_code"] == "000001.SH"
        assert result[0]["trade_date"] == date(2026, 2, 17)
        assert result[0]["ma5"] == Decimal("3200.0")
        assert result[0]["macd_hist"] == Decimal("6.4")  # raw macd → macd_hist
        assert result[0]["atr14"] == Decimal("45.0")  # raw atr → atr14

    def test_empty(self):
        from app.data.etl import transform_tushare_index_technical
        assert transform_tushare_index_technical([]) == []

    def test_nan_fields(self):
        from app.data.etl import transform_tushare_index_technical

        raw = [{"ts_code": "000001.SH", "trade_date": "20260217",
                "ma5": None, "ma10": float("nan"), "ma20": None,
                "ma60": None, "ma120": None, "ma250": None,
                "macd_dif": None, "macd_dea": None, "macd": None,
                "kdj_k": None, "kdj_d": None, "kdj_j": None,
                "rsi6": None, "rsi12": None, "rsi24": None,
                "boll_upper": None, "boll_mid": None, "boll_lower": None,
                "atr": None, "cci": None, "wr": None}]
        result = transform_tushare_index_technical(raw)
        assert len(result) == 1
        assert result[0]["ma5"] is None
        assert result[0]["ma10"] is None  # NaN → None


class TestTransformTushareConceptIndex:
    """transform_tushare_concept_index 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_concept_index

        raw = [{"ts_code": "885720.TI", "name": "半导体", "type": "N"}]
        result = transform_tushare_concept_index(raw, src="THS")
        assert len(result) == 1
        assert result[0]["ts_code"] == "885720.TI"
        assert result[0]["name"] == "半导体"
        assert result[0]["src"] == "THS"
        assert result[0]["type"] == "N"

    def test_dc_source(self):
        from app.data.etl import transform_tushare_concept_index

        raw = [{"ts_code": "BK0001", "name": "新能源", "type": None}]
        result = transform_tushare_concept_index(raw, src="DC")
        assert len(result) == 1
        assert result[0]["src"] == "DC"

    def test_empty(self):
        from app.data.etl import transform_tushare_concept_index
        assert transform_tushare_concept_index([], src="THS") == []


class TestTransformTushareConceptDaily:
    """transform_tushare_concept_daily 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_concept_daily

        raw = [{"ts_code": "885720.TI", "trade_date": "20260217",
                "open": 1200.5, "high": 1250.0, "low": 1180.0,
                "close": 1240.0, "pre_close": 1200.0,
                "change": 40.0, "pct_chg": 3.33,
                "vol": 5000000.0, "amount": 6000000.0}]
        result = transform_tushare_concept_daily(raw)
        assert len(result) == 1
        assert result[0]["ts_code"] == "885720.TI"
        assert result[0]["trade_date"] == date(2026, 2, 17)
        assert result[0]["close"] == Decimal("1240.0")
        assert result[0]["vol"] == Decimal("5000000.0")

    def test_empty(self):
        from app.data.etl import transform_tushare_concept_daily
        assert transform_tushare_concept_daily([]) == []


class TestTransformTushareConceptMember:
    """transform_tushare_concept_member 测试。"""

    def test_normal(self):
        from app.data.etl import transform_tushare_concept_member

        raw = [{"ts_code": "885720.TI", "code": "600519.SH",
                "in_date": "20200101", "out_date": None}]
        result = transform_tushare_concept_member(raw)
        assert len(result) == 1
        assert result[0]["concept_code"] == "885720.TI"
        assert result[0]["stock_code"] == "600519.SH"
        assert result[0]["in_date"] == date(2020, 1, 1)
        assert result[0]["out_date"] is None

    def test_empty(self):
        from app.data.etl import transform_tushare_concept_member
        assert transform_tushare_concept_member([]) == []
