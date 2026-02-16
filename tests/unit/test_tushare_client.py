"""TushareClient 单元测试。

测试 Tushare Pro API 客户端的核心功能：
- 令牌桶限流
- 异步包装
- 重试机制
- DataSourceClient Protocol 方法
- fetch_raw_* 系列方法
"""

from __future__ import annotations

import asyncio
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.data.tushare import TushareClient, _TokenBucket
from app.exceptions import DataSourceError


class TestTokenBucket:
    """令牌桶限流器测试。"""

    @pytest.mark.asyncio
    async def test_acquire_single_token(self) -> None:
        """获取单个令牌应立即返回。"""
        bucket = _TokenBucket(rate_per_minute=60)
        await bucket.acquire()
        assert bucket._tokens < 60.0

    @pytest.mark.asyncio
    async def test_acquire_multiple_tokens_with_wait(self) -> None:
        """连续获取多个令牌时应等待补充。"""
        bucket = _TokenBucket(rate_per_minute=6)  # 0.1 token/sec，很慢

        # 快速消耗所有令牌
        for _ in range(6):
            await bucket.acquire()

        # 此时桶已空，下一个令牌需要等待
        start = asyncio.get_event_loop().time()
        await bucket.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # 应该等待了一段时间（至少 0.5 秒）
        assert elapsed > 0.5

    @pytest.mark.asyncio
    async def test_refill_over_time(self) -> None:
        """令牌应随时间自动补充。"""
        bucket = _TokenBucket(rate_per_minute=60)

        # 消耗一些令牌
        await bucket.acquire()
        await bucket.acquire()
        tokens_after_consume = bucket._tokens

        # 等待 1 秒让令牌补充
        await asyncio.sleep(1.0)
        bucket._refill()

        # 令牌数应该增加
        assert bucket._tokens > tokens_after_consume


class TestTushareClient:
    """TushareClient 核心功能测试。"""

    @pytest.fixture
    def mock_pro_api(self) -> MagicMock:
        """Mock Tushare Pro API。"""
        mock_api = MagicMock()
        return mock_api

    @pytest.fixture
    def client(self, mock_pro_api: MagicMock) -> TushareClient:
        """创建测试用 TushareClient。"""
        with patch("app.data.tushare.ts.pro_api", return_value=mock_pro_api):
            return TushareClient(
                token="test_token",
                retry_count=2,
                retry_interval=0.1,
                qps_limit=60,
            )

    @pytest.mark.asyncio
    async def test_health_check_success(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """健康检查成功应返回 True。"""
        mock_df = pd.DataFrame({"cal_date": ["20240101"]})
        mock_pro_api.query.return_value = mock_df

        result = await client.health_check()

        assert result is True
        mock_pro_api.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """健康检查失败应返回 False。"""
        mock_pro_api.query.side_effect = Exception("API Error")

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_fetch_stock_list(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """获取股票列表应返回标准化格式。"""
        mock_df = pd.DataFrame({
            "ts_code": ["600519.SH", "000001.SZ"],
            "symbol": ["600519", "000001"],
            "name": ["贵州茅台", "平安银行"],
            "area": ["贵州", "广东"],
            "industry": ["白酒", "银行"],
            "market": ["主板", "主板"],
            "list_date": ["20010827", "19910403"],
            "delist_date": [None, None],
            "list_status": ["L", "L"],
        })
        # fetch_stock_list 会循环调用 3 次（L/D/P 状态）
        mock_pro_api.query.return_value = mock_df

        result = await client.fetch_stock_list()

        # 3 次调用 × 2 条记录 = 6 条
        assert len(result) == 6
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["name"] == "贵州茅台"
        assert result[1]["ts_code"] == "000001.SZ"

    @pytest.mark.asyncio
    async def test_fetch_trade_calendar(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """获取交易日历应返回标准化格式。"""
        mock_df = pd.DataFrame({
            "cal_date": ["20240101", "20240102"],
            "is_open": [0, 1],
            "pretrade_date": ["20231229", "20240101"],
        })
        mock_pro_api.query.return_value = mock_df

        result = await client.fetch_trade_calendar(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
        )

        assert len(result) == 2
        assert result[0]["cal_date"] == "20240101"
        assert result[0]["is_open"] is False
        assert result[1]["is_open"] is True

    @pytest.mark.asyncio
    async def test_fetch_daily(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """获取日线数据应合并三个接口的数据。"""
        # Mock daily 接口
        mock_daily = pd.DataFrame({
            "ts_code": ["600519.SH"],
            "trade_date": ["20240101"],
            "open": [1700.0],
            "high": [1720.0],
            "low": [1695.0],
            "close": [1710.0],
            "pre_close": [1705.0],
            "vol": [12345.0],
            "amount": [210000.0],
            "pct_chg": [0.29],
        })

        # Mock adj_factor 接口
        mock_adj = pd.DataFrame({
            "trade_date": ["20240101"],
            "adj_factor": [1.234567],
        })

        # Mock daily_basic 接口
        mock_basic = pd.DataFrame({
            "trade_date": ["20240101"],
            "turnover_rate": [0.56],
        })

        mock_pro_api.query.side_effect = [mock_daily, mock_adj, mock_basic]

        result = await client.fetch_daily(
            code="600519.SH",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 1),
        )

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["close"] == Decimal("1710.0")
        assert result[0]["adj_factor"] == Decimal("1.234567")
        assert result[0]["turnover_rate"] == Decimal("0.56")

    @pytest.mark.asyncio
    async def test_fetch_raw_daily(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """按日期获取全市场日线数据。"""
        mock_df = pd.DataFrame({
            "ts_code": ["600519.SH", "000001.SZ"],
            "trade_date": ["20240101", "20240101"],
            "open": [1700.0, 10.5],
            "close": [1710.0, 10.6],
        })
        mock_pro_api.query.return_value = mock_df

        result = await client.fetch_raw_daily(trade_date="20240101")

        assert len(result) == 2
        assert result[0]["ts_code"] == "600519.SH"
        assert result[1]["ts_code"] == "000001.SZ"

    @pytest.mark.asyncio
    async def test_fetch_raw_fina_indicator(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """按季度获取财务指标（VIP 接口）。"""
        mock_df = pd.DataFrame({
            "ts_code": ["600519.SH"],
            "ann_date": ["20240430"],
            "end_date": ["20231231"],
            "eps": [45.67],
            "roe": [28.56],
        })
        mock_pro_api.query.return_value = mock_df

        result = await client.fetch_raw_fina_indicator(period="20231231")

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"
        assert result[0]["eps"] == 45.67

    @pytest.mark.asyncio
    async def test_fetch_raw_moneyflow(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """获取个股资金流向数据。"""
        mock_df = pd.DataFrame({
            "ts_code": ["600519.SH"],
            "trade_date": ["20240101"],
            "buy_sm_vol": [1000.0],
            "sell_sm_vol": [800.0],
        })
        mock_pro_api.query.return_value = mock_df

        result = await client.fetch_raw_moneyflow(trade_date="20240101")

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"

    @pytest.mark.asyncio
    async def test_fetch_raw_top_list(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """获取龙虎榜数据。"""
        mock_df = pd.DataFrame({
            "ts_code": ["600519.SH"],
            "trade_date": ["20240101"],
            "name": ["贵州茅台"],
            "close": [1710.0],
        })
        mock_pro_api.query.return_value = mock_df

        result = await client.fetch_raw_top_list(trade_date="20240101")

        assert len(result) == 1
        assert result[0]["ts_code"] == "600519.SH"

    @pytest.mark.asyncio
    async def test_retry_on_failure(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """API 调用失败时应自动重试。"""
        # 前两次失败，第三次成功
        mock_pro_api.query.side_effect = [
            Exception("Network Error"),
            Exception("Timeout"),
            pd.DataFrame({"cal_date": ["20240101"]}),
        ]

        result = await client.health_check()

        assert result is True
        assert mock_pro_api.query.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(
        self, client: TushareClient, mock_pro_api: MagicMock
    ) -> None:
        """重试耗尽后应抛出 DataSourceError。"""
        mock_pro_api.query.side_effect = Exception("Persistent Error")

        with pytest.raises(DataSourceError) as exc_info:
            await client._call("test_api")

        assert "重试 2 次后" in str(exc_info.value)
        assert mock_pro_api.query.call_count == 3  # 初始 + 2 次重试

    @pytest.mark.asyncio
    async def test_to_decimal_conversion(self) -> None:
        """测试数值转换为 Decimal。"""
        assert TushareClient._to_decimal(123.45) == Decimal("123.45")
        assert TushareClient._to_decimal("678.90") == Decimal("678.90")
        assert TushareClient._to_decimal(None) is None
        assert TushareClient._to_decimal(float("nan")) is None
        assert TushareClient._to_decimal("invalid") is None
