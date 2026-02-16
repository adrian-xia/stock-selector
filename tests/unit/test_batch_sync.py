"""batch_sync_daily 单元测试（Tushare 按日期模式）。"""

import logging
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.data.batch import batch_sync_daily


# ============================================================
# 辅助
# ============================================================

def _mock_manager() -> MagicMock:
    """创建 mock 的 DataManager。"""
    manager = MagicMock()
    manager.sync_raw_daily = AsyncMock(return_value={"daily": 5000, "adj_factor": 5000, "daily_basic": 5000})
    manager.etl_daily = AsyncMock(return_value={"inserted": 5000})
    return manager


# ============================================================
# 1. 基本功能
# ============================================================

class TestBatchSyncBasic:
    """批量同步基本功能测试。"""

    async def test_sync_multiple_dates(self) -> None:
        """多个交易日应全部同步成功。"""
        manager = _mock_manager()
        dates = [date(2026, 2, 10), date(2026, 2, 11), date(2026, 2, 12)]

        result = await batch_sync_daily(
            session_factory=MagicMock(),
            trade_dates=dates,
            manager=manager,
        )

        assert result["success"] == 3
        assert result["failed"] == 0
        assert result["failed_dates"] == []
        assert manager.sync_raw_daily.call_count == 3
        assert manager.etl_daily.call_count == 3

    async def test_empty_date_list(self) -> None:
        """空日期列表应返回全零结果。"""
        manager = _mock_manager()

        result = await batch_sync_daily(
            session_factory=MagicMock(),
            trade_dates=[],
            manager=manager,
        )

        assert result["success"] == 0
        assert result["failed"] == 0
        assert manager.sync_raw_daily.call_count == 0


# ============================================================
# 2. 错误隔离
# ============================================================

class TestErrorIsolation:
    """错误隔离测试。"""

    async def test_single_failure_continues(self) -> None:
        """单个日期失败不应阻断其他日期的同步。"""
        manager = _mock_manager()
        call_count = 0

        async def _sync_with_failure(td):
            nonlocal call_count
            call_count += 1
            if td == date(2026, 2, 11):
                raise RuntimeError("network error")
            return {"daily": 5000, "adj_factor": 5000, "daily_basic": 5000}

        manager.sync_raw_daily = AsyncMock(side_effect=_sync_with_failure)

        dates = [date(2026, 2, 10), date(2026, 2, 11), date(2026, 2, 12)]
        result = await batch_sync_daily(
            session_factory=MagicMock(),
            trade_dates=dates,
            manager=manager,
        )

        assert result["success"] == 2
        assert result["failed"] == 1
        assert date(2026, 2, 11) in result["failed_dates"]
        assert call_count == 3

    async def test_all_failures(self) -> None:
        """全部失败时应正确统计。"""
        manager = _mock_manager()
        manager.sync_raw_daily = AsyncMock(side_effect=RuntimeError("fail"))

        dates = [date(2026, 2, 10), date(2026, 2, 11)]
        result = await batch_sync_daily(
            session_factory=MagicMock(),
            trade_dates=dates,
            manager=manager,
        )

        assert result["success"] == 0
        assert result["failed"] == 2
        assert len(result["failed_dates"]) == 2


# ============================================================
# 3. 自动创建 manager
# ============================================================

class TestAutoCreateManager:
    """不传 manager 时自动创建。"""

    @patch("app.data.batch.TushareClient")
    @patch("app.data.batch.DataManager")
    async def test_creates_manager_when_none(
        self, mock_manager_cls: MagicMock, mock_client_cls: MagicMock,
    ) -> None:
        """未传入 manager 时应自动创建 TushareClient + DataManager。"""
        mock_manager = _mock_manager()
        mock_manager_cls.return_value = mock_manager

        result = await batch_sync_daily(
            session_factory=MagicMock(),
            trade_dates=[date(2026, 2, 10)],
        )

        mock_client_cls.assert_called_once()
        mock_manager_cls.assert_called_once()
        assert result["success"] == 1


# ============================================================
# 4. 进度日志输出
# ============================================================

class TestProgressLogging:
    """进度日志测试。"""

    async def test_completion_logged(self, caplog) -> None:
        """完成后应输出汇总日志。"""
        manager = _mock_manager()
        dates = [date(2026, 2, 10), date(2026, 2, 11)]

        with caplog.at_level(logging.INFO, logger="app.data.batch"):
            await batch_sync_daily(
                session_factory=MagicMock(),
                trade_dates=dates,
                manager=manager,
            )

        summary_logs = [r for r in caplog.records if "完成" in r.message and "成功" in r.message]
        assert len(summary_logs) >= 1


# ============================================================
# 5. 返回结果字段
# ============================================================

class TestSummaryStats:
    """最终汇总统计测试。"""

    async def test_summary_fields(self) -> None:
        """返回结果应包含所有必要字段。"""
        manager = _mock_manager()

        result = await batch_sync_daily(
            session_factory=MagicMock(),
            trade_dates=[date(2026, 2, 10)],
            manager=manager,
        )

        assert "success" in result
        assert "failed" in result
        assert "failed_dates" in result
        assert "elapsed_seconds" in result
        assert isinstance(result["elapsed_seconds"], float)
