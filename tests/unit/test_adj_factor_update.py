"""batch_update_adj_factor 单元测试。"""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.data.adj_factor import batch_update_adj_factor


def _mock_session_factory(rowcount: int = 5):
    """创建模拟的 async session factory。"""
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.rowcount = rowcount
    session.execute.return_value = result_mock

    ctx = AsyncMock()
    ctx.__aenter__.return_value = session
    ctx.__aexit__.return_value = False

    factory = MagicMock()
    factory.return_value = ctx
    return factory, session


class TestBatchUpdateAdjFactor:
    """批量更新复权因子测试。"""

    async def test_empty_records(self) -> None:
        """空记录列表应返回 0。"""
        factory, _ = _mock_session_factory()
        result = await batch_update_adj_factor(factory, "600519.SH", [])
        assert result == 0

    async def test_single_dividend_date(self) -> None:
        """单个除权日应执行 2 次 UPDATE（区间 + 之前的填充）。"""
        factory, session = _mock_session_factory(rowcount=100)
        records = [
            {"trade_date": "2024-06-19", "adj_factor": Decimal("0.949509")},
        ]

        result = await batch_update_adj_factor(factory, "600519.SH", records)

        # 1 次区间更新（最后一个除权日到未来）+ 1 次之前的填充
        assert session.execute.call_count == 2
        session.commit.assert_called_once()

    async def test_multiple_dividend_dates(self) -> None:
        """多个除权日应按区间分别更新。"""
        factory, session = _mock_session_factory(rowcount=50)
        records = [
            {"trade_date": "2024-06-19", "adj_factor": Decimal("0.949509")},
            {"trade_date": "2024-12-20", "adj_factor": Decimal("0.964356")},
            {"trade_date": "2025-06-26", "adj_factor": Decimal("0.983256")},
        ]

        result = await batch_update_adj_factor(factory, "600519.SH", records)

        # 3 次区间更新 + 1 次之前的填充 = 4 次 execute
        assert session.execute.call_count == 4
        session.commit.assert_called_once()

    async def test_records_sorted_by_date(self) -> None:
        """乱序输入应自动按日期排序。"""
        factory, session = _mock_session_factory(rowcount=10)
        records = [
            {"trade_date": "2024-12-20", "adj_factor": Decimal("0.964356")},
            {"trade_date": "2024-06-19", "adj_factor": Decimal("0.949509")},
        ]

        await batch_update_adj_factor(factory, "600519.SH", records)

        # 验证第一次 execute 使用的是较早的日期
        first_call_params = session.execute.call_args_list[0][0][1]
        assert first_call_params["start_date"] == date(2024, 6, 19)
        assert first_call_params["end_date"] == date(2024, 12, 20)

    async def test_no_matching_rows(self) -> None:
        """无匹配行时应正常完成（rowcount=0）。"""
        factory, session = _mock_session_factory(rowcount=0)
        records = [
            {"trade_date": "2099-01-01", "adj_factor": Decimal("1.000000")},
        ]

        result = await batch_update_adj_factor(factory, "600519.SH", records)
        assert result == 0
        session.commit.assert_called_once()
