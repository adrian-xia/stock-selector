"""测试 P4 板块日线补追。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.data.manager import DataManager


def _make_manager_with_session(mock_session):
    """创建测试用 DataManager。"""
    session_factory = MagicMock()
    session_factory.return_value.__aenter__.return_value = mock_session
    return DataManager(
        session_factory=session_factory,
        clients={"tushare": AsyncMock()},
        primary="tushare",
    )


@pytest.mark.asyncio
async def test_gap_fill_concept_daily_fills_missing_dates():
    """应补拉缺失交易日并补算板块技术指标。"""
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_result.fetchall.return_value = [(date(2026, 3, 4),)]
    mock_session.execute.return_value = existing_result

    manager = _make_manager_with_session(mock_session)
    manager.get_trade_calendar = AsyncMock(
        return_value=[date(2026, 3, 4), date(2026, 3, 5), date(2026, 3, 6)]
    )
    manager.sync_concept_daily = AsyncMock(
        side_effect=[
            {"raw_inserted": 1200, "cleaned_inserted": 1180},
            {"raw_inserted": 1100, "cleaned_inserted": 1088},
        ]
    )
    manager.update_concept_indicators = AsyncMock(
        side_effect=[
            {"success": 1},
            {"success": 1},
        ]
    )

    result = await manager.gap_fill_concept_daily(
        start_date=date(2026, 3, 4),
        end_date=date(2026, 3, 6),
    )

    assert result["checked_dates"] == 3
    assert result["missing_dates"] == ["2026-03-05", "2026-03-06"]
    assert result["filled_dates"] == 2
    assert result["raw_inserted"] == 2300
    assert result["cleaned_inserted"] == 2268
    assert result["tech_success"] == 2
    assert manager.sync_concept_daily.await_count == 2
    manager.update_concept_indicators.assert_any_await(date(2026, 3, 5))
    manager.update_concept_indicators.assert_any_await(date(2026, 3, 6))


@pytest.mark.asyncio
async def test_gap_fill_concept_daily_no_missing_dates():
    """无缺口时不应重复同步。"""
    mock_session = AsyncMock()
    existing_result = MagicMock()
    existing_result.fetchall.return_value = [
        (date(2026, 3, 4),),
        (date(2026, 3, 5),),
        (date(2026, 3, 6),),
    ]
    mock_session.execute.return_value = existing_result

    manager = _make_manager_with_session(mock_session)
    manager.get_trade_calendar = AsyncMock(
        return_value=[date(2026, 3, 4), date(2026, 3, 5), date(2026, 3, 6)]
    )
    manager.sync_concept_daily = AsyncMock()
    manager.update_concept_indicators = AsyncMock()

    result = await manager.gap_fill_concept_daily(
        start_date=date(2026, 3, 4),
        end_date=date(2026, 3, 6),
    )

    assert result["missing_dates"] == []
    assert result["filled_dates"] == 0
    manager.sync_concept_daily.assert_not_awaited()
    manager.update_concept_indicators.assert_not_awaited()
