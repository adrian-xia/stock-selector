"""测试数据嗅探模块。"""

import pytest
from datetime import date
from unittest.mock import AsyncMock, MagicMock

from app.data.probe import probe_daily_data


@pytest.mark.asyncio
async def test_probe_daily_data_success():
    """测试数据嗅探成功场景（样本股票有数据）。"""
    # 模拟 session_factory
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 4  # 5 只样本股票中有 4 只有数据（80%）
    mock_session.execute.return_value = mock_result

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    # 执行嗅探
    result = await probe_daily_data(
        session_factory=mock_session_factory,
        target_date=date(2026, 2, 10),
        probe_stocks=["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
        threshold=0.8,
    )

    # 验证结果
    assert result is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_probe_daily_data_failure():
    """测试数据嗅探失败场景（样本股票无数据）。"""
    # 模拟 session_factory
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 2  # 5 只样本股票中只有 2 只有数据（40%）
    mock_session.execute.return_value = mock_result

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    # 执行嗅探
    result = await probe_daily_data(
        session_factory=mock_session_factory,
        target_date=date(2026, 2, 10),
        probe_stocks=["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
        threshold=0.8,
    )

    # 验证结果
    assert result is False
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_probe_daily_data_no_data():
    """测试无任何数据场景。"""
    # 模拟 session_factory
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 0  # 所有样本股票都没有数据
    mock_session.execute.return_value = mock_result

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    # 执行嗅探
    result = await probe_daily_data(
        session_factory=mock_session_factory,
        target_date=date(2026, 2, 10),
        probe_stocks=["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
        threshold=0.8,
    )

    # 验证结果
    assert result is False
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_probe_daily_data_threshold():
    """测试阈值计算逻辑。"""
    # 模拟 session_factory
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 9  # 10 只样本股票中有 9 只有数据（90%）
    mock_session.execute.return_value = mock_result

    mock_session_factory = MagicMock()
    mock_session_factory.return_value.__aenter__.return_value = mock_session

    # 执行嗅探（阈值 90%）
    result = await probe_daily_data(
        session_factory=mock_session_factory,
        target_date=date(2026, 2, 10),
        probe_stocks=[f"60051{i}.SH" for i in range(10)],
        threshold=0.9,
    )

    # 验证结果
    assert result is True
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_probe_daily_data_empty_stocks():
    """测试样本股票列表为空的场景。"""
    mock_session_factory = MagicMock()

    # 执行嗅探
    result = await probe_daily_data(
        session_factory=mock_session_factory,
        target_date=date(2026, 2, 10),
        probe_stocks=[],
        threshold=0.8,
    )

    # 验证结果
    assert result is False
