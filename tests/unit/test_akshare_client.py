"""AKShareClient 单元测试。"""

import math
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.data.akshare import AKShareClient, _dec, _infer_exchange
from app.exceptions import DataSourceError


# ---------------------------------------------------------------------------
# _infer_exchange 交易所推断
# ---------------------------------------------------------------------------
class TestInferExchange:
    """根据股票代码前缀推断交易所。"""

    def test_sh_prefix_6(self) -> None:
        """6 开头 -> SH（上交所）。"""
        assert _infer_exchange("600000") == "SH"
        assert _infer_exchange("601398") == "SH"
        assert _infer_exchange("688001") == "SH"

    def test_sz_prefix_0(self) -> None:
        """0 开头 -> SZ（深交所）。"""
        assert _infer_exchange("000001") == "SZ"
        assert _infer_exchange("002594") == "SZ"

    def test_sz_prefix_3(self) -> None:
        """3 开头 -> SZ（创业板）。"""
        assert _infer_exchange("300750") == "SZ"
        assert _infer_exchange("301001") == "SZ"

    def test_bj_prefix_8(self) -> None:
        """8 开头 -> BJ（北交所）。"""
        assert _infer_exchange("830799") == "BJ"
        assert _infer_exchange("871981") == "BJ"

    def test_bj_prefix_4(self) -> None:
        """4 开头 -> BJ（北交所）。"""
        assert _infer_exchange("430047") == "BJ"

    def test_unknown_prefix_defaults_sz(self) -> None:
        """未知前缀默认返回 SZ。"""
        assert _infer_exchange("999999") == "SZ"
        assert _infer_exchange("100000") == "SZ"


# ---------------------------------------------------------------------------
# _dec Decimal 转换
# ---------------------------------------------------------------------------
class TestDec:
    """_dec 函数：安全地将值转换为 Decimal。"""

    def test_none_returns_none(self) -> None:
        assert _dec(None) is None

    def test_float_nan_returns_none(self) -> None:
        assert _dec(float("nan")) is None

    def test_math_nan_returns_none(self) -> None:
        assert _dec(math.nan) is None

    def test_normal_int(self) -> None:
        result = _dec(100)
        assert result == Decimal("100")

    def test_normal_float(self) -> None:
        result = _dec(3.14)
        assert isinstance(result, Decimal)
        assert result == Decimal("3.14")

    def test_normal_string(self) -> None:
        result = _dec("99.5")
        assert result == Decimal("99.5")

    def test_invalid_string_returns_none(self) -> None:
        assert _dec("not_a_number") is None
        assert _dec("") is None

    def test_zero(self) -> None:
        assert _dec(0) == Decimal("0")

    def test_negative(self) -> None:
        assert _dec(-5.5) == Decimal("-5.5")


# ---------------------------------------------------------------------------
# _PLACEHOLDER_FETCH_DAILY
# ---------------------------------------------------------------------------

# 构造 akshare 返回的 DataFrame 辅助函数
def _make_daily_df() -> pd.DataFrame:
    """构造一行模拟 ak.stock_zh_a_hist 返回的 DataFrame。"""
    return pd.DataFrame([{
        "日期": "2025-01-02",
        "开盘": 10.5,
        "收盘": 11.0,
        "最高": 11.2,
        "最低": 10.3,
        "成交量": 100000,
        "成交额": 1100000.0,
        "振幅": 8.65,
        "涨跌幅": 4.76,
        "涨跌额": 0.5,
        "换手率": 1.23,
    }])


# ---------------------------------------------------------------------------
# AKShareClient._fetch_daily_sync
# ---------------------------------------------------------------------------
class TestFetchDailySync:
    """日线数据解析测试。"""

    @patch("app.data.akshare.ak.stock_zh_a_hist")
    def test_normal_parse(self, mock_hist: MagicMock) -> None:
        """正常解析一行日线数据。"""
        mock_hist.return_value = _make_daily_df()

        rows = AKShareClient._fetch_daily_sync(
            "600000", date(2025, 1, 1), date(2025, 1, 3)
        )

        assert len(rows) == 1
        row = rows[0]
        assert row["ts_code"] == "600000.SH"
        assert row["trade_date"] == "2025-01-02"
        assert row["open"] == Decimal("10.5")
        assert row["close"] == Decimal("11.0")
        assert row["high"] == Decimal("11.2")
        assert row["low"] == Decimal("10.3")
        assert row["vol"] == Decimal("100000")
        assert row["amount"] == Decimal("1100000.0")
        assert row["turnover_rate"] == Decimal("1.23")
        assert row["pct_chg"] == Decimal("4.76")
        assert row["pre_close"] is None
        assert row["trade_status"] == "1"

    @patch("app.data.akshare.ak.stock_zh_a_hist")
    def test_code_with_dot_prefix(self, mock_hist: MagicMock) -> None:
        """带交易所后缀的代码（如 600000.SH）应正确拆分。"""
        mock_hist.return_value = _make_daily_df()

        rows = AKShareClient._fetch_daily_sync(
            "600000.SH", date(2025, 1, 1), date(2025, 1, 3)
        )

        assert len(rows) == 1
        assert rows[0]["ts_code"] == "600000.SH"
        # 确认传给 akshare 的 symbol 是纯数字
        mock_hist.assert_called_once_with(
            symbol="600000",
            period="daily",
            start_date="20250101",
            end_date="20250103",
            adjust="",
        )

    @patch("app.data.akshare.ak.stock_zh_a_hist")
    def test_sz_code_exchange(self, mock_hist: MagicMock) -> None:
        """深交所代码推断为 SZ。"""
        mock_hist.return_value = _make_daily_df()

        rows = AKShareClient._fetch_daily_sync(
            "000001", date(2025, 1, 1), date(2025, 1, 3)
        )

        assert rows[0]["ts_code"] == "000001.SZ"

    @patch("app.data.akshare.ak.stock_zh_a_hist")
    def test_empty_df_returns_empty(self, mock_hist: MagicMock) -> None:
        """空 DataFrame 返回空列表。"""
        mock_hist.return_value = pd.DataFrame()

        rows = AKShareClient._fetch_daily_sync(
            "600000", date(2025, 1, 1), date(2025, 1, 3)
        )

        assert rows == []

    @patch("app.data.akshare.ak.stock_zh_a_hist")
    def test_none_df_returns_empty(self, mock_hist: MagicMock) -> None:
        """返回 None 时返回空列表。"""
        mock_hist.return_value = None

        rows = AKShareClient._fetch_daily_sync(
            "600000", date(2025, 1, 1), date(2025, 1, 3)
        )

        assert rows == []

    @patch("app.data.akshare.ak.stock_zh_a_hist")
    def test_nan_values_become_none(self, mock_hist: MagicMock) -> None:
        """DataFrame 中的 NaN 值应转换为 None。"""
        df = pd.DataFrame([{
            "日期": "2025-01-02",
            "开盘": float("nan"),
            "收盘": 11.0,
            "最高": float("nan"),
            "最低": 10.3,
            "成交量": 100000,
            "成交额": float("nan"),
            "振幅": 8.65,
            "涨跌幅": 4.76,
            "涨跌额": 0.5,
            "换手率": float("nan"),
        }])
        mock_hist.return_value = df

        rows = AKShareClient._fetch_daily_sync(
            "600000", date(2025, 1, 1), date(2025, 1, 3)
        )

        assert rows[0]["open"] is None
        assert rows[0]["high"] is None
        assert rows[0]["amount"] is None
        assert rows[0]["turnover_rate"] is None
        # 非 NaN 字段正常解析
        assert rows[0]["close"] == Decimal("11.0")
        assert rows[0]["low"] == Decimal("10.3")


# ---------------------------------------------------------------------------
# AKShareClient._fetch_stock_list_sync
# ---------------------------------------------------------------------------
class TestFetchStockListSync:
    """股票列表获取测试。"""

    @patch("app.data.akshare.ak.stock_info_a_code_name")
    def test_normal_parse(self, mock_info: MagicMock) -> None:
        """正常解析股票列表。"""
        mock_info.return_value = pd.DataFrame([
            {"code": "600000", "name": "浦发银行"},
            {"code": "000001", "name": "平安银行"},
            {"code": "830799", "name": "艾融软件"},
        ])

        rows = AKShareClient._fetch_stock_list_sync()

        assert len(rows) == 3
        assert rows[0]["ts_code"] == "600000.SH"
        assert rows[0]["symbol"] == "600000"
        assert rows[0]["name"] == "浦发银行"
        assert rows[0]["list_status"] == "L"

        assert rows[1]["ts_code"] == "000001.SZ"
        assert rows[1]["name"] == "平安银行"

        assert rows[2]["ts_code"] == "830799.BJ"
        assert rows[2]["name"] == "艾融软件"

    @patch("app.data.akshare.ak.stock_info_a_code_name")
    def test_empty_df_returns_empty(self, mock_info: MagicMock) -> None:
        """空 DataFrame 返回空列表。"""
        mock_info.return_value = pd.DataFrame()

        rows = AKShareClient._fetch_stock_list_sync()

        assert rows == []

    @patch("app.data.akshare.ak.stock_info_a_code_name")
    def test_none_df_returns_empty(self, mock_info: MagicMock) -> None:
        """返回 None 时返回空列表。"""
        mock_info.return_value = None

        rows = AKShareClient._fetch_stock_list_sync()

        assert rows == []

    @patch("app.data.akshare.ak.stock_info_a_code_name")
    def test_default_fields(self, mock_info: MagicMock) -> None:
        """默认字段值检查。"""
        mock_info.return_value = pd.DataFrame([
            {"code": "300750", "name": "宁德时代"},
        ])

        rows = AKShareClient._fetch_stock_list_sync()

        row = rows[0]
        assert row["industry"] == ""
        assert row["area"] == ""
        assert row["market"] == ""
        assert row["list_date"] == ""
        assert row["list_status"] == "L"


# ---------------------------------------------------------------------------
# AKShareClient._with_retry 重试机制
# ---------------------------------------------------------------------------
class TestWithRetry:
    """重试机制测试。"""

    async def test_success_no_retry(self) -> None:
        """首次成功不触发重试。"""
        client = AKShareClient(retry_count=3, retry_interval=0.01, qps_limit=5)

        sync_fn = MagicMock(return_value="ok")
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value="ok"):
            result = await client._with_retry(sync_fn)

        assert result == "ok"

    async def test_retry_then_success(self) -> None:
        """失败后重试成功。"""
        client = AKShareClient(retry_count=2, retry_interval=0.01, qps_limit=5)

        call_count = 0

        async def mock_to_thread(fn, *args):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("network error")
            return "recovered"

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._with_retry(lambda: None)

        assert result == "recovered"
        assert call_count == 2

    async def test_all_retries_exhausted_raises(self) -> None:
        """所有重试耗尽后抛出 DataSourceError。"""
        client = AKShareClient(retry_count=2, retry_interval=0.01, qps_limit=5)

        async def mock_to_thread(fn, *args):
            raise ConnectionError("persistent failure")

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(DataSourceError, match="AKShare failed after 2 retries"):
                    await client._with_retry(lambda: None)

    async def test_retry_count_zero_no_retry(self) -> None:
        """retry_count=0 时不重试，直接抛出。"""
        client = AKShareClient(retry_count=0, retry_interval=0.01, qps_limit=5)

        async def mock_to_thread(fn, *args):
            raise RuntimeError("immediate failure")

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with pytest.raises(DataSourceError, match="AKShare failed after 0 retries"):
                await client._with_retry(lambda: None)

    async def test_retry_uses_exponential_backoff(self) -> None:
        """重试间隔使用指数退避：interval * 2^attempt。"""
        client = AKShareClient(retry_count=3, retry_interval=1.0, qps_limit=5)

        call_count = 0

        async def mock_to_thread(fn, *args):
            nonlocal call_count
            call_count += 1
            raise ConnectionError("fail")

        sleep_values: list[float] = []

        async def mock_sleep(seconds: float) -> None:
            sleep_values.append(seconds)

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with patch("asyncio.sleep", side_effect=mock_sleep):
                with pytest.raises(DataSourceError):
                    await client._with_retry(lambda: None)

        # retry_interval=1.0, 退避: 1.0*2^0=1.0, 1.0*2^1=2.0, 1.0*2^2=4.0
        assert sleep_values == [1.0, 2.0, 4.0]
        # 总调用次数 = 1 初始 + 3 重试 = 4
        assert call_count == 4

    async def test_original_exception_chained(self) -> None:
        """DataSourceError 应链式包含原始异常。"""
        client = AKShareClient(retry_count=0, retry_interval=0.01, qps_limit=5)

        original = ValueError("original cause")

        async def mock_to_thread(fn, *args):
            raise original

        with patch("asyncio.to_thread", side_effect=mock_to_thread):
            with pytest.raises(DataSourceError) as exc_info:
                await client._with_retry(lambda: None)

        assert exc_info.value.__cause__ is original
