"""测试回测 API：任务列表接口。"""

import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.backtest import list_backtest_tasks


class TestListBacktestTasks:
    """测试回测任务列表端点。"""

    @patch("app.api.backtest.async_session_factory")
    async def test_returns_paginated_list(self, mock_factory: MagicMock) -> None:
        """正常查询应返回分页列表。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # 第一次调用返回总数
        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 2

        # 第二次调用返回任务列表
        mock_list_result = MagicMock()
        mock_list_result.mappings.return_value.all.return_value = [
            {
                "id": 2,
                "strategy_name": "rsi_oversold",
                "stock_codes": json.dumps(["000001.SZ"]),
                "start_date": date(2024, 6, 1),
                "end_date": date(2025, 6, 1),
                "status": "completed",
                "created_at": datetime(2026, 2, 8, 11, 0, 0),
                "annual_return": 0.15,
            },
            {
                "id": 1,
                "strategy_name": "ma_cross",
                "stock_codes": ["600519.SH", "000001.SZ"],
                "start_date": date(2024, 1, 1),
                "end_date": date(2025, 12, 31),
                "status": "failed",
                "created_at": datetime(2026, 2, 8, 10, 0, 0),
                "annual_return": None,
            },
        ]

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        response = await list_backtest_tasks(page=1, page_size=20)

        assert response.total == 2
        assert response.page == 1
        assert response.page_size == 20
        assert len(response.items) == 2
        assert response.items[0].task_id == 2
        assert response.items[0].stock_count == 1
        assert response.items[0].annual_return == 0.15
        assert response.items[1].annual_return is None

    @patch("app.api.backtest.async_session_factory")
    async def test_empty_list(self, mock_factory: MagicMock) -> None:
        """无任务时应返回空列表。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_list_result = MagicMock()
        mock_list_result.mappings.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        response = await list_backtest_tasks(page=1, page_size=20)

        assert response.total == 0
        assert response.items == []

    @patch("app.api.backtest.async_session_factory")
    async def test_page_size_capped_at_100(self, mock_factory: MagicMock) -> None:
        """page_size 超过 100 时应被截断为 100。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_count_result = MagicMock()
        mock_count_result.scalar_one.return_value = 0

        mock_list_result = MagicMock()
        mock_list_result.mappings.return_value.all.return_value = []

        mock_session.execute.side_effect = [mock_count_result, mock_list_result]

        response = await list_backtest_tasks(page=1, page_size=500)

        assert response.page_size == 100
