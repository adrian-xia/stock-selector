"""测试数据嗅探模块。"""

from datetime import date
from unittest.mock import AsyncMock, patch

import pytest

from app.data.probe import probe_daily_data


@pytest.mark.asyncio
async def test_probe_daily_data_success():
    """测试数据嗅探成功场景（Tushare 返回样本股票数据）。"""
    mock_client = AsyncMock()
    mock_client.fetch_raw_daily.return_value = [
        {"ts_code": "600519.SH"},
        {"ts_code": "000001.SZ"},
        {"ts_code": "600036.SH"},
        {"ts_code": "000858.SZ"},
    ]

    with patch("app.data.probe.TushareClient", return_value=mock_client):
        result = await probe_daily_data(
            session_factory=AsyncMock(),
            target_date=date(2026, 2, 10),
            probe_stocks=["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
            threshold=0.8,
        )

    assert result is True
    mock_client.fetch_raw_daily.assert_awaited_once_with(trade_date="20260210")


@pytest.mark.asyncio
async def test_probe_daily_data_failure():
    """测试数据嗅探失败场景（样本覆盖率不足）。"""
    mock_client = AsyncMock()
    mock_client.fetch_raw_daily.return_value = [
        {"ts_code": "600519.SH"},
        {"ts_code": "000001.SZ"},
    ]

    with patch("app.data.probe.TushareClient", return_value=mock_client):
        result = await probe_daily_data(
            session_factory=AsyncMock(),
            target_date=date(2026, 2, 10),
            probe_stocks=["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
            threshold=0.8,
        )

    assert result is False
    mock_client.fetch_raw_daily.assert_awaited_once_with(trade_date="20260210")


@pytest.mark.asyncio
async def test_probe_daily_data_no_data():
    """测试无任何数据场景。"""
    mock_client = AsyncMock()
    mock_client.fetch_raw_daily.return_value = []

    with patch("app.data.probe.TushareClient", return_value=mock_client):
        result = await probe_daily_data(
            session_factory=AsyncMock(),
            target_date=date(2026, 2, 10),
            probe_stocks=["600519.SH", "000001.SZ", "600036.SH", "000858.SZ", "601318.SH"],
            threshold=0.8,
        )

    assert result is False
    mock_client.fetch_raw_daily.assert_awaited_once_with(trade_date="20260210")


@pytest.mark.asyncio
async def test_probe_daily_data_threshold():
    """测试阈值计算逻辑。"""
    mock_client = AsyncMock()
    mock_client.fetch_raw_daily.return_value = [
        {"ts_code": f"60051{i}.SH"} for i in range(9)
    ]

    with patch("app.data.probe.TushareClient", return_value=mock_client):
        result = await probe_daily_data(
            session_factory=AsyncMock(),
            target_date=date(2026, 2, 10),
            probe_stocks=[f"60051{i}.SH" for i in range(10)],
            threshold=0.9,
        )

    assert result is True
    mock_client.fetch_raw_daily.assert_awaited_once_with(trade_date="20260210")


@pytest.mark.asyncio
async def test_probe_daily_data_empty_stocks():
    """测试样本股票列表为空的场景。"""
    mock_session_factory = AsyncMock()

    result = await probe_daily_data(
        session_factory=mock_session_factory,
        target_date=date(2026, 2, 10),
        probe_stocks=[],
        threshold=0.8,
    )

    assert result is False
