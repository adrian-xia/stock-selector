"""测试数据完整性检查功能。"""

import pytest
from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.data.manager import DataManager
from app.scheduler.core import check_data_integrity


@pytest.mark.asyncio
async def test_detect_missing_dates_no_missing():
    """测试 detect_missing_dates() - 无缺失数据场景。"""
    # 模拟 DataManager
    manager = MagicMock(spec=DataManager)

    # 模拟交易日历：2026-02-03, 2026-02-04, 2026-02-05
    trading_dates = [
        date(2026, 2, 3),
        date(2026, 2, 4),
        date(2026, 2, 5),
    ]
    manager.get_trade_calendar = AsyncMock(return_value=trading_dates)

    # 模拟已有数据：全部交易日都有数据
    manager._session_factory = MagicMock()
    session_mock = MagicMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    result_mock = MagicMock()
    result_mock.all.return_value = [
        (date(2026, 2, 3),),
        (date(2026, 2, 4),),
        (date(2026, 2, 5),),
    ]
    session_mock.execute = AsyncMock(return_value=result_mock)
    manager._session_factory.return_value = session_mock

    # 调用真实的 detect_missing_dates 方法
    from app.data.manager import DataManager as RealDataManager

    real_manager = RealDataManager(
        session_factory=manager._session_factory,
        clients={},
        primary="baostock",
    )
    real_manager.get_trade_calendar = manager.get_trade_calendar

    start_date = date(2026, 2, 3)
    end_date = date(2026, 2, 5)
    missing_dates = await real_manager.detect_missing_dates(start_date, end_date)

    # 验证：无缺失日期
    assert missing_dates == []


@pytest.mark.asyncio
async def test_detect_missing_dates_partial_missing():
    """测试 detect_missing_dates() - 部分缺失数据场景。"""
    # 模拟 DataManager
    manager = MagicMock(spec=DataManager)

    # 模拟交易日历：2026-02-03, 2026-02-04, 2026-02-05
    trading_dates = [
        date(2026, 2, 3),
        date(2026, 2, 4),
        date(2026, 2, 5),
    ]
    manager.get_trade_calendar = AsyncMock(return_value=trading_dates)

    # 模拟已有数据：只有 2026-02-03 有数据
    manager._session_factory = MagicMock()
    session_mock = MagicMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    result_mock = MagicMock()
    result_mock.all.return_value = [
        (date(2026, 2, 3),),
    ]
    session_mock.execute = AsyncMock(return_value=result_mock)
    manager._session_factory.return_value = session_mock

    # 调用真实的 detect_missing_dates 方法
    from app.data.manager import DataManager as RealDataManager

    real_manager = RealDataManager(
        session_factory=manager._session_factory,
        clients={},
        primary="baostock",
    )
    real_manager.get_trade_calendar = manager.get_trade_calendar

    start_date = date(2026, 2, 3)
    end_date = date(2026, 2, 5)
    missing_dates = await real_manager.detect_missing_dates(start_date, end_date)

    # 验证：缺失 2026-02-04 和 2026-02-05
    assert missing_dates == [date(2026, 2, 4), date(2026, 2, 5)]


@pytest.mark.asyncio
async def test_detect_missing_dates_all_missing():
    """测试 detect_missing_dates() - 全部缺失数据场景。"""
    # 模拟 DataManager
    manager = MagicMock(spec=DataManager)

    # 模拟交易日历：2026-02-03, 2026-02-04, 2026-02-05
    trading_dates = [
        date(2026, 2, 3),
        date(2026, 2, 4),
        date(2026, 2, 5),
    ]
    manager.get_trade_calendar = AsyncMock(return_value=trading_dates)

    # 模拟已有数据：无数据
    manager._session_factory = MagicMock()
    session_mock = MagicMock()
    session_mock.__aenter__ = AsyncMock(return_value=session_mock)
    session_mock.__aexit__ = AsyncMock(return_value=None)

    result_mock = MagicMock()
    result_mock.all.return_value = []
    session_mock.execute = AsyncMock(return_value=result_mock)
    manager._session_factory.return_value = session_mock

    # 调用真实的 detect_missing_dates 方法
    from app.data.manager import DataManager as RealDataManager

    real_manager = RealDataManager(
        session_factory=manager._session_factory,
        clients={},
        primary="baostock",
    )
    real_manager.get_trade_calendar = manager.get_trade_calendar

    start_date = date(2026, 2, 3)
    end_date = date(2026, 2, 5)
    missing_dates = await real_manager.detect_missing_dates(start_date, end_date)

    # 验证：全部缺失
    assert missing_dates == trading_dates


@pytest.mark.asyncio
async def test_check_data_integrity_skip():
    """测试启动时数据完整性检查 - 跳过检查。"""
    with patch("app.scheduler.core.settings") as mock_settings:
        mock_settings.data_integrity_check_enabled = True
        mock_settings.data_integrity_check_days = 30

        # 调用检查函数，跳过检查
        await check_data_integrity(skip_check=True)

        # 验证：无异常抛出，函数正常返回


@pytest.mark.asyncio
async def test_check_data_integrity_disabled():
    """测试启动时数据完整性检查 - 配置禁用。"""
    with patch("app.scheduler.core.settings") as mock_settings:
        mock_settings.data_integrity_check_enabled = False
        mock_settings.data_integrity_check_days = 30

        # 调用检查函数
        await check_data_integrity(skip_check=False)

        # 验证：无异常抛出，函数正常返回
