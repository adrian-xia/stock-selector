"""BaoStockClient.fetch_adj_factor 单元测试。"""

from decimal import Decimal
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from app.data.baostock import BaoStockClient
from app.exceptions import DataSourceError


def _make_client() -> BaoStockClient:
    """创建测试用客户端，显式传参避免读取 settings。"""
    return BaoStockClient(retry_count=0, retry_interval=0.01, qps_limit=5)


class _FakeResultSet:
    """模拟 BaoStock ResultSet，支持迭代。"""

    def __init__(self, rows: list[list[str]], fields: list[str], error_code: str = "0", error_msg: str = "") -> None:
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


# ============================================================
# 1. _fetch_adj_factor_sync 同步方法测试
# ============================================================

class TestFetchAdjFactorSync:
    """测试 _fetch_adj_factor_sync 同步方法。"""

    @patch("app.data.baostock.bs")
    def test_basic_return_format(self, mock_bs: MagicMock) -> None:
        """返回 list[dict]，每个 dict 含 ts_code, trade_date, adj_factor。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[
                ["sh.600519", "2025-01-02", "1.000000", "100.000000"],
                ["sh.600519", "2025-01-03", "1.000000", "100.000000"],
            ],
            fields=["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor"],
        )

        client = _make_client()
        result = client._fetch_adj_factor_sync("600519.SH", date(2025, 1, 2), date(2025, 1, 3))

        assert len(result) == 2
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["trade_date"] == "2025-01-02"
        assert isinstance(result[0]["adj_factor"], Decimal)
        assert result[0]["adj_factor"] == Decimal("1.000000")

    @patch("app.data.baostock.bs")
    def test_code_conversion(self, mock_bs: MagicMock) -> None:
        """BaoStock 代码应转换为标准格式。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[["sz.000001", "2025-06-15", "0.850000", "120.000000"]],
            fields=["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor"],
        )

        client = _make_client()
        result = client._fetch_adj_factor_sync("000001.SZ", date(2025, 6, 15), date(2025, 6, 15))

        assert result[0]["ts_code"] == "000001.SZ"
        # 验证传给 BaoStock 的代码格式
        mock_bs.query_adjust_factor.assert_called_once_with(
            code="sz.000001",
            start_date="2025-06-15",
            end_date="2025-06-15",
        )

    @patch("app.data.baostock.bs")
    def test_skip_empty_adj_factor(self, mock_bs: MagicMock) -> None:
        """空的 foreAdjustFactor 应被跳过。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[
                ["sh.600519", "2025-01-02", "1.000000", "100.000000"],
                ["sh.600519", "2025-01-03", "", "100.000000"],
                ["sh.600519", "2025-01-04", "N/A", "100.000000"],
            ],
            fields=["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor"],
        )

        client = _make_client()
        result = client._fetch_adj_factor_sync("600519.SH", date(2025, 1, 2), date(2025, 1, 4))

        assert len(result) == 1
        assert result[0]["trade_date"] == "2025-01-02"

    @patch("app.data.baostock.bs")
    def test_api_error_raises(self, mock_bs: MagicMock) -> None:
        """BaoStock API 错误应抛出 DataSourceError。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[], fields=[], error_code="10001", error_msg="query error",
        )

        client = _make_client()
        with pytest.raises(DataSourceError, match="adj_factor query failed"):
            client._fetch_adj_factor_sync("600519.SH", date(2025, 1, 2), date(2025, 1, 3))

    @patch("app.data.baostock.bs")
    def test_login_logout_called(self, mock_bs: MagicMock) -> None:
        """每次调用应 login/logout。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[], fields=["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor"],
        )

        client = _make_client()
        client._fetch_adj_factor_sync("600519.SH", date(2025, 1, 2), date(2025, 1, 3))

        mock_bs.login.assert_called_once()
        mock_bs.logout.assert_called_once()

    @patch("app.data.baostock.bs")
    def test_adj_factor_with_dividends(self, mock_bs: MagicMock) -> None:
        """有除权除息时，adj_factor 应在除权日发生变化。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[
                ["sz.000001", "2024-07-11", "1.000000", "50.000000"],
                ["sz.000001", "2024-07-12", "0.980000", "51.020408"],
            ],
            fields=["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor"],
        )

        client = _make_client()
        result = client._fetch_adj_factor_sync("000001.SZ", date(2024, 7, 11), date(2024, 7, 12))

        assert len(result) == 2
        assert result[0]["adj_factor"] == Decimal("1.000000")
        assert result[1]["adj_factor"] == Decimal("0.980000")
        assert result[0]["adj_factor"] != result[1]["adj_factor"]


# ============================================================
# 2. fetch_adj_factor 异步方法测试
# ============================================================

class TestFetchAdjFactorAsync:
    """测试 fetch_adj_factor 异步公开方法。"""

    @patch("app.data.baostock.bs")
    async def test_async_wrapper(self, mock_bs: MagicMock) -> None:
        """异步方法应正确包装同步方法。"""
        mock_bs.login.return_value = MagicMock(error_code="0")
        mock_bs.query_adjust_factor.return_value = _FakeResultSet(
            rows=[["sh.600519", "2025-01-02", "1.000000", "100.000000"]],
            fields=["code", "dividOperateDate", "foreAdjustFactor", "backAdjustFactor"],
        )

        client = _make_client()
        result = await client.fetch_adj_factor("600519.SH", date(2025, 1, 2), date(2025, 1, 2))

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"
