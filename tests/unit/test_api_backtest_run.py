"""测试回测 API：run 和 result 端点。"""

import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.backtest import (
    BacktestRunRequest,
    get_backtest_result,
    run_backtest_api,
)


def _mock_session_factory():
    """创建 mock 的 async_session_factory。"""
    mock_session = AsyncMock()
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_factory, mock_session


class TestRunBacktestApi:
    """测试 POST /backtest/run 端点。"""

    async def test_invalid_date_range_returns_400(self) -> None:
        """start_date >= end_date 应返回 400。"""
        req = BacktestRunRequest(
            strategy_name="ma-cross",
            stock_codes=["600519.SH"],
            start_date=date(2025, 12, 31),
            end_date=date(2025, 1, 1),
            initial_capital=1_000_000,
        )
        with pytest.raises(HTTPException) as exc_info:
            await run_backtest_api(req)
        assert exc_info.value.status_code == 400

    async def test_same_date_returns_400(self) -> None:
        """start_date == end_date 应返回 400。"""
        req = BacktestRunRequest(
            strategy_name="ma-cross",
            stock_codes=["600519.SH"],
            start_date=date(2025, 6, 1),
            end_date=date(2025, 6, 1),
            initial_capital=1_000_000,
        )
        with pytest.raises(HTTPException) as exc_info:
            await run_backtest_api(req)
        assert exc_info.value.status_code == 400

    @patch("app.api.backtest.run_backtest", new_callable=AsyncMock)
    @patch("app.api.backtest.BacktestResultWriter")
    @patch("app.api.backtest.async_session_factory")
    async def test_run_success(
        self,
        mock_factory: MagicMock,
        mock_writer_cls: MagicMock,
        mock_run_bt: AsyncMock,
    ) -> None:
        """正常执行应返回 completed 状态。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # 策略查询结果
        mock_strategy_result = MagicMock()
        mock_strategy_result.scalar_one_or_none.return_value = 1

        # INSERT 返回 task_id
        mock_insert_result = MagicMock()
        mock_insert_result.scalar_one.return_value = 42
        mock_update_result = MagicMock()
        mock_session.execute.side_effect = [mock_strategy_result, mock_insert_result, mock_update_result]

        # 模拟回测结果
        mock_run_bt.return_value = {
            "strategy_instance": MagicMock(),
            "equity_curve": [{"date": "2025-01-02", "value": 1000000}],
            "trades_log": [],
            "elapsed_ms": 200,
        }

        mock_writer = AsyncMock()
        mock_writer_cls.return_value = mock_writer

        # 模拟查询结果（第二个 session context）
        mock_res_row = MagicMock()
        mock_res_row.mappings.return_value.first.return_value = {
            "total_return": 0.1,
            "annual_return": 0.12,
            "max_drawdown": -0.05,
            "sharpe_ratio": 1.5,
            "win_rate": 0.6,
            "profit_loss_ratio": 2.0,
            "total_trades": 10,
            "calmar_ratio": 2.4,
            "sortino_ratio": 1.8,
            "volatility": 0.15,
        }

        mock_session2 = AsyncMock()
        mock_session2.execute.return_value = mock_res_row
        call_count = [0]

        async def side_effect_aenter(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return mock_session
            return mock_session2

        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=side_effect_aenter)

        req = BacktestRunRequest(
            strategy_name="ma-cross",
            stock_codes=["600519.SH"],
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            initial_capital=1_000_000,
        )
        response = await run_backtest_api(req)

        assert response.task_id == 42
        assert response.status == "completed"
        assert response.result is not None
        assert response.result.total_return == 0.1

    @patch("app.api.backtest.run_backtest", new_callable=AsyncMock)
    @patch("app.api.backtest.BacktestResultWriter")
    @patch("app.api.backtest.async_session_factory")
    async def test_run_failure_returns_failed(
        self,
        mock_factory: MagicMock,
        mock_writer_cls: MagicMock,
        mock_run_bt: AsyncMock,
    ) -> None:
        """回测执行失败应返回 failed 状态。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        # 策略查询结果
        mock_strategy_result = MagicMock()
        mock_strategy_result.scalar_one_or_none.return_value = 1

        mock_insert_result = MagicMock()
        mock_insert_result.scalar_one.return_value = 99
        mock_update_result = MagicMock()
        mock_session.execute.side_effect = [mock_strategy_result, mock_insert_result, mock_update_result]

        mock_run_bt.side_effect = RuntimeError("数据不足")

        mock_writer = AsyncMock()
        mock_writer_cls.return_value = mock_writer

        req = BacktestRunRequest(
            strategy_name="ma-cross",
            stock_codes=["600519.SH"],
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
        )
        response = await run_backtest_api(req)

        assert response.task_id == 99
        assert response.status == "failed"
        assert "数据不足" in response.error_message
        mock_writer.mark_failed.assert_awaited_once()


class TestGetBacktestResult:
    """测试 GET /backtest/result/{task_id} 端点。"""

    @patch("app.api.backtest.async_session_factory")
    async def test_not_found_returns_404(self, mock_factory: MagicMock) -> None:
        """查询不存在的任务应返回 404。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = None
        mock_session.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_backtest_result(task_id=9999)
        assert exc_info.value.status_code == 404

    @patch("app.api.backtest.async_session_factory")
    async def test_running_task(self, mock_factory: MagicMock) -> None:
        """查询运行中的任务应返回 running 状态。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "id": 1,
            "strategy_name": "ma-cross",
            "status": "running",
        }
        mock_session.execute.return_value = mock_result

        response = await get_backtest_result(task_id=1)
        assert response.status == "running"
        assert response.result is None

    @patch("app.api.backtest.async_session_factory")
    async def test_failed_task(self, mock_factory: MagicMock) -> None:
        """查询失败的任务应返回 error_message。"""
        mock_session = AsyncMock()
        mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_result = MagicMock()
        mock_result.mappings.return_value.first.return_value = {
            "id": 2,
            "strategy_name": "rsi-oversold",
            "status": "failed",
            "error_message": "数据不足",
        }
        mock_session.execute.return_value = mock_result

        response = await get_backtest_result(task_id=2)
        assert response.status == "failed"
        assert response.error_message == "数据不足"

    @patch("app.api.backtest.async_session_factory")
    async def test_completed_task_with_full_result(
        self, mock_factory: MagicMock
    ) -> None:
        """查询已完成任务应返回完整结果。"""
        mock_session1 = AsyncMock()
        task_result = MagicMock()
        task_result.mappings.return_value.first.return_value = {
            "id": 3,
            "strategy_name": "ma-cross",
            "stock_codes": json.dumps(["600519.SH"]),
            "start_date": date(2024, 1, 1),
            "end_date": date(2025, 12, 31),
            "status": "completed",
        }
        mock_session1.execute.return_value = task_result

        mock_session2 = AsyncMock()
        res_result = MagicMock()
        res_result.mappings.return_value.first.return_value = {
            "total_return": 0.25,
            "annual_return": 0.12,
            "max_drawdown": -0.08,
            "sharpe_ratio": 1.2,
            "win_rate": 0.55,
            "profit_loss_ratio": 1.8,
            "total_trades": 5,
            "calmar_ratio": 1.5,
            "sortino_ratio": 1.3,
            "volatility": 0.2,
            "trades_json": json.dumps([{
                "stock_code": "600519.SH",
                "direction": "buy",
                "date": "2024-03-01",
                "price": 1700.0,
                "size": 100,
                "commission": 4.25,
                "pnl": 0.0,
            }]),
            "equity_curve_json": json.dumps([
                {"date": "2024-01-02", "value": 1000000.0},
                {"date": "2024-01-03", "value": 1005000.0},
            ]),
        }
        mock_session2.execute.return_value = res_result

        call_count = [0]

        async def side_effect_aenter(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 1:
                return mock_session1
            return mock_session2

        mock_factory.return_value.__aenter__ = AsyncMock(side_effect=side_effect_aenter)
        mock_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        response = await get_backtest_result(task_id=3)

        assert response.status == "completed"
        assert response.result.total_return == 0.25
        assert response.result.total_trades == 5
        assert len(response.trades) == 1
        assert response.trades[0].stock_code == "600519.SH"
        assert len(response.equity_curve) == 2
        assert response.stock_codes == ["600519.SH"]
