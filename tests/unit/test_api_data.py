"""测试数据查询 API：K 线数据接口。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.data import get_kline


class TestGetKline:
    """测试 K 线数据查询端点。"""

    @patch("app.api.data.async_session_factory")
    async def test_returns_kline_data(self, mock_factory: MagicMock) -> None:
        """正常查询应返回 OHLCV 数据。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # 模拟数据库返回（按 trade_date DESC）
        mock_rows = [
            {
                "trade_date": date(2025, 1, 3),
                "open": 1700.0,
                "high": 1720.0,
                "low": 1690.0,
                "close": 1710.0,
                "vol": 20000.0,
            },
            {
                "trade_date": date(2025, 1, 2),
                "open": 1680.0,
                "high": 1700.0,
                "low": 1675.0,
                "close": 1695.0,
                "vol": 15000.0,
            },
        ]
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = mock_rows
        mock_session.execute.return_value = mock_result

        response = await get_kline(ts_code="600519.SH", limit=120)

        assert response.ts_code == "600519.SH"
        assert len(response.data) == 2
        # 应按日期升序返回（reversed）
        assert response.data[0].date == "2025-01-02"
        assert response.data[1].date == "2025-01-03"
        assert response.data[0].close == 1695.0

    @patch("app.api.data.async_session_factory")
    async def test_empty_result(self, mock_factory: MagicMock) -> None:
        """无数据时应返回空数组。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        response = await get_kline(ts_code="999999.SH", limit=120)

        assert response.ts_code == "999999.SH"
        assert response.data == []

    @patch("app.api.data.async_session_factory")
    async def test_with_date_range(self, mock_factory: MagicMock) -> None:
        """指定日期范围时应传递参数。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        await get_kline(
            ts_code="600519.SH",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 12, 31),
            limit=120,
        )

        # 验证 execute 被调用，且 SQL 包含日期条件
        call_args = mock_session.execute.call_args
        sql_text = str(call_args[0][0].text)
        assert "start_date" in sql_text
        assert "end_date" in sql_text
