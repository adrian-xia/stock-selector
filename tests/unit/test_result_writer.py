"""测试回测结果写入器。

测试绩效指标提取和 JSON 序列化逻辑，不依赖数据库。
"""

import math
from unittest.mock import MagicMock

import pytest

from app.backtest.writer import (
    _safe_float,
    _to_json_str,
    calc_extra_metrics,
    extract_metrics,
)


def _make_mock_strategy(
    sharpe: float | None = 1.5,
    max_dd: float = 15.0,
    total_return: float = 0.30,
    annual_return: float = 0.15,
    total_trades: int = 10,
    won: int = 6,
    lost: int = 4,
    avg_won_pnl: float = 5000.0,
    avg_lost_pnl: float = -2000.0,
) -> MagicMock:
    """构造模拟的 Backtrader 策略实例。"""
    strat = MagicMock()

    # SharpeRatio analyzer
    strat.analyzers.sharpe.get_analysis.return_value = {
        "sharperatio": sharpe,
    }

    # DrawDown analyzer
    strat.analyzers.drawdown.get_analysis.return_value = {
        "max": {"drawdown": max_dd},
    }

    # Returns analyzer
    strat.analyzers.returns.get_analysis.return_value = {
        "rtot": total_return,
        "rnorm": annual_return,
    }

    # TradeAnalyzer
    strat.analyzers.trades.get_analysis.return_value = {
        "total": {"total": total_trades},
        "won": {"total": won, "pnl": {"average": avg_won_pnl}},
        "lost": {"total": lost, "pnl": {"average": avg_lost_pnl}},
    }

    return strat


class TestExtractMetrics:
    """测试从 Analyzers 提取绩效指标。"""

    def test_normal_extraction(self) -> None:
        """正常提取所有指标。"""
        strat = _make_mock_strategy()
        metrics = extract_metrics(strat, 1_000_000)

        assert metrics["sharpe_ratio"] == 1.5
        assert metrics["max_drawdown"] == 0.15  # 15% → 0.15
        assert metrics["total_return"] == 0.30
        assert metrics["annual_return"] == 0.15
        assert metrics["total_trades"] == 10
        assert metrics["win_rate"] == 0.6  # 6/10
        assert metrics["profit_loss_ratio"] == 2.5  # 5000/2000

    def test_zero_trades(self) -> None:
        """零交易时 win_rate 为 None。"""
        strat = _make_mock_strategy(
            total_trades=0, won=0, lost=0,
            avg_won_pnl=0, avg_lost_pnl=0,
        )
        metrics = extract_metrics(strat, 1_000_000)

        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] is None

    def test_nan_sharpe(self) -> None:
        """NaN 的 Sharpe Ratio 应返回 None。"""
        strat = _make_mock_strategy(sharpe=float("nan"))
        metrics = extract_metrics(strat, 1_000_000)
        assert metrics["sharpe_ratio"] is None

    def test_none_sharpe(self) -> None:
        """None 的 Sharpe Ratio 应返回 None。"""
        strat = _make_mock_strategy(sharpe=None)
        metrics = extract_metrics(strat, 1_000_000)
        assert metrics["sharpe_ratio"] is None

    def test_no_losses(self) -> None:
        """无亏损交易时 profit_loss_ratio 为 None。"""
        strat = _make_mock_strategy(
            total_trades=5, won=5, lost=0,
            avg_won_pnl=3000, avg_lost_pnl=0,
        )
        metrics = extract_metrics(strat, 1_000_000)
        assert metrics["profit_loss_ratio"] is None


class TestCalcExtraMetrics:
    """测试额外指标计算。"""

    def test_calmar_ratio(self) -> None:
        """Calmar Ratio = annual_return / max_drawdown。"""
        metrics = {
            "annual_return": 0.20,
            "max_drawdown": 0.10,
        }
        equity_curve = [
            {"date": "2024-01-02", "value": 1000000},
            {"date": "2024-01-03", "value": 1010000},
        ]
        result = calc_extra_metrics(equity_curve, metrics)
        assert result["calmar_ratio"] == 2.0

    def test_calmar_ratio_zero_drawdown(self) -> None:
        """最大回撤为 0 时 Calmar Ratio 为 None。"""
        metrics = {"annual_return": 0.20, "max_drawdown": 0}
        result = calc_extra_metrics(
            [{"date": "2024-01-02", "value": 1000000}], metrics
        )
        assert result["calmar_ratio"] is None

    def test_volatility_calculation(self) -> None:
        """年化波动率计算。"""
        # 构造有波动的净值曲线（涨跌交替）
        equity_curve = [
            {"date": "2024-01-02", "value": 1000000},
            {"date": "2024-01-03", "value": 1020000},  # +2%
            {"date": "2024-01-04", "value": 990000},   # -2.94%
            {"date": "2024-01-05", "value": 1015000},   # +2.53%
            {"date": "2024-01-08", "value": 985000},   # -2.96%
            {"date": "2024-01-09", "value": 1010000},   # +2.54%
            {"date": "2024-01-10", "value": 995000},   # -1.49%
            {"date": "2024-01-11", "value": 1025000},   # +3.02%
            {"date": "2024-01-12", "value": 1005000},   # -1.95%
            {"date": "2024-01-15", "value": 1030000},   # +2.49%
        ]
        metrics = {"annual_return": 0.10, "max_drawdown": 0.05}
        result = calc_extra_metrics(equity_curve, metrics)

        assert result["volatility"] is not None
        assert result["volatility"] > 0

    def test_volatility_single_point(self) -> None:
        """单个数据点时波动率为 None。"""
        metrics = {"annual_return": 0.10, "max_drawdown": 0.05}
        result = calc_extra_metrics(
            [{"date": "2024-01-02", "value": 1000000}], metrics
        )
        assert result["volatility"] is None

    def test_sortino_ratio(self) -> None:
        """Sortino Ratio 使用下行标准差。"""
        # 构造有涨有跌的净值曲线
        equity_curve = [
            {"date": "2024-01-02", "value": 1000000},
            {"date": "2024-01-03", "value": 1010000},  # +1%
            {"date": "2024-01-04", "value": 990000},   # -1.98%
            {"date": "2024-01-05", "value": 1005000},   # +1.52%
            {"date": "2024-01-08", "value": 985000},   # -1.99%
        ]
        metrics = {"annual_return": 0.10, "max_drawdown": 0.05}
        result = calc_extra_metrics(equity_curve, metrics)

        assert result["sortino_ratio"] is not None

    def test_sortino_no_downside(self) -> None:
        """无下行收益时 Sortino Ratio 为 None。"""
        equity_curve = [
            {"date": f"2024-01-{i+2:02d}", "value": 1000000 + i * 10000}
            for i in range(5)
        ]
        metrics = {"annual_return": 0.10, "max_drawdown": 0.05}
        result = calc_extra_metrics(equity_curve, metrics)
        assert result["sortino_ratio"] is None


class TestSafeFloat:
    """测试安全浮点转换。"""

    def test_normal_float(self) -> None:
        assert _safe_float(1.5) == 1.5

    def test_int_to_float(self) -> None:
        assert _safe_float(3) == 3.0

    def test_none_returns_none(self) -> None:
        assert _safe_float(None) is None

    def test_nan_returns_none(self) -> None:
        assert _safe_float(float("nan")) is None

    def test_inf_returns_none(self) -> None:
        assert _safe_float(float("inf")) is None

    def test_string_returns_none(self) -> None:
        assert _safe_float("abc") is None


class TestToJsonStr:
    """测试 JSON 序列化。"""

    def test_empty_list(self) -> None:
        assert _to_json_str([]) == "[]"

    def test_trade_list(self) -> None:
        trades = [{"stock_code": "600519.SH", "pnl": 1000.5}]
        result = _to_json_str(trades)
        assert '"600519.SH"' in result
        assert "1000.5" in result

    def test_chinese_characters(self) -> None:
        """中文字符不应被转义。"""
        data = [{"name": "贵州茅台"}]
        result = _to_json_str(data)
        assert "贵州茅台" in result
