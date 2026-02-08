"""BaoStockClient 单元测试。"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.baostock import BaoStockClient
from app.exceptions import DataSourceError


# --- 辅助：构造客户端实例（不依赖 settings） ---

def _make_client(**kwargs) -> BaoStockClient:
    """创建测试用客户端，显式传参避免读取 settings。"""
    defaults = dict(retry_count=2, retry_interval=0.01, qps_limit=5)
    defaults.update(kwargs)
    return BaoStockClient(**defaults)


# ============================================================
# 1. 标准代码 <-> BaoStock 代码互转
# ============================================================

class TestCodeConversion:
    """股票代码格式转换测试。"""

    # --- _to_baostock_code: 标准 -> BaoStock ---

    def test_sh_to_baostock(self) -> None:
        """上海市场：600519.SH -> sh.600519"""
        assert BaoStockClient._to_baostock_code("600519.SH") == "sh.600519"

    def test_sz_to_baostock(self) -> None:
        """深圳市场：000001.SZ -> sz.000001"""
        assert BaoStockClient._to_baostock_code("000001.SZ") == "sz.000001"

    def test_baostock_code_lowercase(self) -> None:
        """转换后市场前缀应为小写。"""
        result = BaoStockClient._to_baostock_code("300750.SZ")
        assert result == "sz.300750"
        assert result.split(".")[0].islower()

    def test_baostock_code_no_dot_passthrough(self) -> None:
        """无点号的代码原样返回。"""
        assert BaoStockClient._to_baostock_code("600519") == "600519"

    # --- _to_standard_code: BaoStock -> 标准 ---

    def test_sh_to_standard(self) -> None:
        """sh.600519 -> 600519.SH"""
        assert BaoStockClient._to_standard_code("sh.600519") == "600519.SH"

    def test_sz_to_standard(self) -> None:
        """sz.000001 -> 000001.SZ"""
        assert BaoStockClient._to_standard_code("sz.000001") == "000001.SZ"

    def test_standard_code_uppercase(self) -> None:
        """转换后市场后缀应为大写。"""
        result = BaoStockClient._to_standard_code("sh.601318")
        assert result == "601318.SH"
        assert result.split(".")[1].isupper()

    def test_standard_code_no_dot_passthrough(self) -> None:
        """无点号的代码原样返回。"""
        assert BaoStockClient._to_standard_code("600519") == "600519"

    # --- 往返转换 ---

    @pytest.mark.parametrize("standard_code", ["600519.SH", "000001.SZ", "300750.SZ"])
    def test_roundtrip(self, standard_code: str) -> None:
        """标准 -> BaoStock -> 标准，往返一致。"""
        bs_code = BaoStockClient._to_baostock_code(standard_code)
        assert BaoStockClient._to_standard_code(bs_code) == standard_code


# ============================================================
# 2. 日线数据解析 (_parse_daily_row)
# ============================================================

class TestParseDailyRow:
    """日线原始数据解析测试。"""

    def _sample_raw(self) -> dict:
        """构造一条完整的 BaoStock 日线原始数据。"""
        return {
            "date": "2025-01-06",
            "code": "sh.600519",
            "open": "1680.0000",
            "high": "1700.0000",
            "low": "1665.0000",
            "close": "1695.0000",
            "preclose": "1678.0000",
            "volume": "3200000",
            "amount": "5400000000.00",
            "turn": "0.254700",
            "tradestatus": "1",
            "pctChg": "1.0131",
            "isST": "0",
        }

    def test_basic_fields(self) -> None:
        """基本字段正确映射。"""
        client = _make_client()
        result = client._parse_daily_row(self._sample_raw())

        assert result["ts_code"] == "600519.SH"
        assert result["trade_date"] == "2025-01-06"
        assert result["trade_status"] == "1"

    def test_decimal_conversion(self) -> None:
        """数值字段转为 Decimal。"""
        client = _make_client()
        result = client._parse_daily_row(self._sample_raw())

        assert result["open"] == Decimal("1680.0000")
        assert result["high"] == Decimal("1700.0000")
        assert result["low"] == Decimal("1665.0000")
        assert result["close"] == Decimal("1695.0000")
        assert result["pre_close"] == Decimal("1678.0000")
        assert result["vol"] == Decimal("3200000")
        assert result["amount"] == Decimal("5400000000.00")
        assert result["turnover_rate"] == Decimal("0.254700")
        assert result["pct_chg"] == Decimal("1.0131")

    @pytest.mark.parametrize("empty_val", ["", "N/A", "--", "None"])
    def test_empty_values_become_none(self, empty_val: str) -> None:
        """空值、N/A、--、None 均解析为 None。"""
        client = _make_client()
        raw = self._sample_raw()
        raw["open"] = empty_val
        result = client._parse_daily_row(raw)
        assert result["open"] is None

    def test_invalid_decimal_becomes_none(self) -> None:
        """无法解析的数值返回 None。"""
        client = _make_client()
        raw = self._sample_raw()
        raw["close"] = "abc"
        result = client._parse_daily_row(raw)
        assert result["close"] is None

    def test_trade_status_not_trading(self) -> None:
        """非交易状态 tradestatus != '1' 时返回 '0'。"""
        client = _make_client()
        raw = self._sample_raw()
        raw["tradestatus"] = "0"
        result = client._parse_daily_row(raw)
        assert result["trade_status"] == "0"

    def test_missing_keys_handled(self) -> None:
        """缺失字段不报错，数值为 None，字符串为空。"""
        client = _make_client()
        result = client._parse_daily_row({})

        assert result["ts_code"] == ""
        assert result["trade_date"] == ""
        assert result["open"] is None
        assert result["close"] is None
        assert result["trade_status"] == "0"


# ============================================================
# 3. 重试机制 (_with_retry)
# ============================================================

class TestWithRetry:
    """异步重试机制测试。"""

    async def test_success_no_retry(self) -> None:
        """首次成功，不触发重试。"""
        client = _make_client()

        mock_fn = lambda: "ok"  # noqa: E731
        with patch("asyncio.to_thread", new_callable=AsyncMock, return_value="ok") as mock_thread:
            result = await client._with_retry(mock_fn)

        assert result == "ok"
        assert mock_thread.call_count == 1

    async def test_first_fail_second_success(self) -> None:
        """首次失败，第二次成功——验证重试生效。"""
        client = _make_client()

        mock_fn = lambda: None  # noqa: E731 — 占位，实际由 to_thread mock 控制
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = [RuntimeError("network error"), "recovered"]
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await client._with_retry(mock_fn)

        assert result == "recovered"
        assert mock_thread.call_count == 2

    async def test_all_retries_exhausted_raises(self) -> None:
        """全部重试耗尽后抛出 DataSourceError。"""
        client = _make_client()  # retry_count=2

        mock_fn = lambda: None  # noqa: E731
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = RuntimeError("persistent failure")
            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(DataSourceError, match="persistent failure"):
                    await client._with_retry(mock_fn)

        # 初始 1 次 + 重试 2 次 = 3 次
        assert mock_thread.call_count == 3

    async def test_retry_exponential_backoff(self) -> None:
        """验证指数退避等待时间。"""
        client = _make_client()  # retry_interval=0.01

        mock_fn = lambda: None  # noqa: E731
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_thread:
            mock_thread.side_effect = RuntimeError("fail")
            with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
                with pytest.raises(DataSourceError):
                    await client._with_retry(mock_fn)

        # retry_interval=0.01, attempt 0: 0.01*2^0=0.01, attempt 1: 0.01*2^1=0.02
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert len(sleep_calls) == 2
        assert sleep_calls[0] == pytest.approx(0.01)
        assert sleep_calls[1] == pytest.approx(0.02)


# ============================================================
# 4. 健康检查 (health_check)
# ============================================================

class TestHealthCheck:
    """健康检查测试。"""

    async def test_healthy(self) -> None:
        """_with_retry 成功时返回 True。"""
        client = _make_client()
        with patch.object(client, "_with_retry", new_callable=AsyncMock, return_value=True):
            assert await client.health_check() is True

    async def test_unhealthy(self) -> None:
        """_with_retry 抛异常时返回 False。"""
        client = _make_client()
        with patch.object(
            client, "_with_retry", new_callable=AsyncMock,
            side_effect=DataSourceError("login failed"),
        ):
            assert await client.health_check() is False


# ============================================================
# 5. 连接池集成
# ============================================================

class _FakeResultSet:
    """模拟 BaoStock ResultSet。"""

    def __init__(
        self, rows: list[list[str]], fields: list[str],
        error_code: str = "0", error_msg: str = "",
    ) -> None:
        self.fields = fields
        self.error_code = error_code
        self.error_msg = error_msg
        self._rows = rows
        self._index = -1

    def next(self) -> bool:
        self._index += 1
        return self._index < len(self._rows)

    def get_row_data(self) -> list[str]:
        return self._rows[self._index]


class TestConnectionPoolIntegration:
    """BaoStockClient 使用连接池时的行为测试。"""

    @patch("app.data.baostock.bs")
    async def test_with_pool_no_login_logout(self, mock_bs: MagicMock) -> None:
        """使用连接池时，不应调用 login/logout。"""
        mock_bs.query_history_k_data_plus.return_value = _FakeResultSet(
            rows=[], fields=[],
        )

        mock_pool = MagicMock()
        mock_session = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_session)
        mock_pool.release = AsyncMock()

        client = _make_client(connection_pool=mock_pool)
        from datetime import date
        await client.fetch_daily("600519.SH", date(2025, 1, 6), date(2025, 1, 6))

        # 不应调用 login/logout
        mock_bs.login.assert_not_called()
        mock_bs.logout.assert_not_called()
        # 应调用 pool.acquire 和 pool.release
        mock_pool.acquire.assert_called_once()
        mock_pool.release.assert_called_once()

    @patch("app.data.baostock.bs")
    async def test_with_pool_release_on_error(self, mock_bs: MagicMock) -> None:
        """使用连接池时，即使查询失败也应 release 连接。"""
        mock_bs.query_history_k_data_plus.return_value = _FakeResultSet(
            rows=[], fields=[], error_code="10001", error_msg="query error",
        )

        mock_pool = MagicMock()
        mock_session = MagicMock()
        mock_pool.acquire = AsyncMock(return_value=mock_session)
        mock_pool.release = AsyncMock()

        client = _make_client(retry_count=0, connection_pool=mock_pool)
        from datetime import date
        with pytest.raises(DataSourceError):
            await client.fetch_daily("600519.SH", date(2025, 1, 6), date(2025, 1, 6))

        # 即使失败也应 release
        mock_pool.release.assert_called_once()


class TestBackwardCompatibility:
    """无连接池时的向后兼容性测试。"""

    @patch("app.data.baostock.bs")
    async def test_without_pool_uses_login_logout(self, mock_bs: MagicMock) -> None:
        """不提供连接池时，应使用旧的 login/logout 逻辑。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_history_k_data_plus.return_value = _FakeResultSet(
            rows=[], fields=[],
        )

        client = _make_client()  # 无连接池
        from datetime import date
        await client.fetch_daily("600519.SH", date(2025, 1, 6), date(2025, 1, 6))

        mock_bs.login.assert_called()
        mock_bs.logout.assert_called()

    def test_default_pool_is_none(self) -> None:
        """默认构造时连接池应为 None。"""
        client = _make_client()
        assert client._pool is None
