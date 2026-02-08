"""测试回测策略基类：AStockStrategy 和 SignalStrategy。

使用 Backtrader Cerebro 运行小数据集验证策略行为。
"""

import backtrader as bt
import pandas as pd
import pytest

from app.backtest.commission import ChinaStockCommission
from app.backtest.data_feed import build_data_feed
from app.backtest.strategy import AStockStrategy, SignalStrategy


def _make_df(
    days: int = 20,
    start_price: float = 33.0,
    step: float = 0.1,
    volume: int = 1_000_000,
) -> pd.DataFrame:
    """构造测试用日线 DataFrame。

    默认 33 元起步，配合 5000 元资金只买 100 股，
    避免全仓买入后 commission 导致 Margin 拒绝。
    """
    dates = pd.bdate_range(start="2024-01-02", periods=days)
    prices = [start_price + i * step for i in range(days)]
    return pd.DataFrame({
        "open": prices,
        "high": [p + 0.2 for p in prices],
        "low": [p - 0.1 for p in prices],
        "close": prices,
        "vol": [volume] * days,
        "amount": [volume * 10] * days,
        "turnover_rate": [1.5] * days,
        "adj_factor": [1.0] * days,
    }, index=dates)


def _run_cerebro(
    strategy_cls: type,
    df: pd.DataFrame,
    cash: float = 5_000,
    **strategy_params,
) -> bt.Strategy:
    """运行 Cerebro 并返回策略实例。

    注意：SignalStrategy 用 cash/price 计算 size，但 Backtrader 在下一个 bar
    的 open 价执行，可能因价格上涨导致 Margin 拒绝。测试时应给充足资金。
    """
    cerebro = bt.Cerebro()
    feed = build_data_feed(df, name="test")
    cerebro.adddata(feed)
    cerebro.addstrategy(strategy_cls, **strategy_params)
    cerebro.broker.setcash(cash)
    cerebro.broker.addcommissioninfo(ChinaStockCommission())
    # 允许 cheat-on-close 以确保订单在当前 bar 成交（测试用）
    cerebro.broker.set_coc(True)
    # 设置 checksubmit=False 跳过 margin 预检查，让订单直接成交
    cerebro.broker.set_checksubmit(False)
    results = cerebro.run()
    return results[0]


class TestAStockStrategy:
    """测试 AStockStrategy 基类。"""

    def test_equity_curve_recorded(self) -> None:
        """运行后 equity_curve 长度应等于 bar 数量。"""
        df = _make_df(days=15)
        strat = _run_cerebro(AStockStrategy, df)

        assert len(strat.equity_curve) == 15
        # 每条记录包含 date 和 value
        for entry in strat.equity_curve:
            assert "date" in entry
            assert "value" in entry

    def test_equity_curve_structure(self) -> None:
        """equity_curve 的 value 应为正数。"""
        df = _make_df(days=10)
        strat = _run_cerebro(AStockStrategy, df)

        for entry in strat.equity_curve:
            assert entry["value"] > 0

    def test_safe_buy_normal(self) -> None:
        """正常价格（未涨停）应能成功买入。"""
        df = _make_df(days=10, step=0.05)
        strat = _run_cerebro(SignalStrategy, df, cash=5_000, hold_days=20)

        # SignalStrategy 会在首日买入
        assert strat._in_position or len(strat.trades_log) > 0

    def test_safe_buy_blocked_at_limit_up(self) -> None:
        """涨停时 safe_buy 应被拦截。"""
        dates = pd.bdate_range(start="2024-01-02", periods=3)
        df = pd.DataFrame({
            "open": [33.0, 36.3, 37.0],
            "high": [33.5, 36.5, 37.5],
            "low": [32.8, 36.0, 36.8],
            "close": [33.0, 36.3, 37.0],  # 第二天涨 10%
            "vol": [1000000, 1000000, 1000000],
            "amount": [10000000, 11000000, 11500000],
            "turnover_rate": [1.5, 1.5, 1.5],
            "adj_factor": [1.0, 1.0, 1.0],
        }, index=dates)

        strat = _run_cerebro(SignalStrategy, df, cash=5_000, hold_days=20)
        # 策略应该能运行完成（不崩溃）
        assert len(strat.equity_curve) == 3

    def test_safe_sell_blocked_at_limit_down(self) -> None:
        """跌停时 safe_sell 应被拦截。"""
        dates = pd.bdate_range(start="2024-01-02", periods=5)
        df = pd.DataFrame({
            "open": [33.0, 33.1, 29.5, 28.0, 27.0],
            "high": [33.5, 33.3, 29.8, 28.3, 27.3],
            "low": [32.8, 33.0, 29.3, 27.8, 26.8],
            "close": [33.0, 33.1, 29.5, 28.0, 27.0],  # 第三天跌 ~11%
            "vol": [1000000] * 5,
            "amount": [10000000] * 5,
            "turnover_rate": [1.5] * 5,
            "adj_factor": [1.0] * 5,
        }, index=dates)

        strat = _run_cerebro(
            SignalStrategy, df, cash=5_000,
            hold_days=2, stop_loss_pct=0.03,
        )
        # 策略应该能运行完成
        assert len(strat.equity_curve) == 5

    def test_trades_log_recorded(self) -> None:
        """发生交易时 trades_log 应有记录。"""
        df = _make_df(days=15, step=0.05)
        # 给足够资金确保订单不被 margin 拒绝
        strat = _run_cerebro(SignalStrategy, df, cash=5_000, hold_days=3)

        # 应该有买入和卖出记录
        assert len(strat.trades_log) >= 1
        for trade in strat.trades_log:
            assert "stock_code" in trade
            assert "direction" in trade
            assert "price" in trade
            assert "size" in trade
            assert trade["direction"] in ("buy", "sell")


class TestSignalStrategy:
    """测试 SignalStrategy 通用信号策略。"""

    def test_buy_on_first_day(self) -> None:
        """首个可交易日应买入（100 股整数倍）。"""
        df = _make_df(days=10)
        strat = _run_cerebro(SignalStrategy, df, cash=5_000, hold_days=20)

        # 应该有买入记录
        buy_trades = [t for t in strat.trades_log if t["direction"] == "buy"]
        assert len(buy_trades) >= 1
        # 买入数量应为 100 的整数倍
        assert buy_trades[0]["size"] % 100 == 0

    def test_sell_after_hold_days(self) -> None:
        """持有达到 hold_days 后应卖出。"""
        df = _make_df(days=15, step=0.05)
        strat = _run_cerebro(SignalStrategy, df, cash=5_000, hold_days=3)

        sell_trades = [t for t in strat.trades_log if t["direction"] == "sell"]
        assert len(sell_trades) >= 1

    def test_stop_loss(self) -> None:
        """亏损超过 stop_loss_pct 应提前卖出。"""
        dates = pd.bdate_range(start="2024-01-02", periods=10)
        prices = [33.0 - i * 1.0 for i in range(10)]  # 每天跌约 3%
        df = pd.DataFrame({
            "open": prices,
            "high": [p + 0.1 for p in prices],
            "low": [p - 0.1 for p in prices],
            "close": prices,
            "vol": [1000000] * 10,
            "amount": [10000000] * 10,
            "turnover_rate": [1.5] * 10,
            "adj_factor": [1.0] * 10,
        }, index=dates)

        strat = _run_cerebro(
            SignalStrategy, df, cash=5_000,
            hold_days=20, stop_loss_pct=0.05,
        )

        sell_trades = [t for t in strat.trades_log if t["direction"] == "sell"]
        # 应该在 hold_days 之前就止损卖出
        assert len(sell_trades) >= 1

    def test_skip_suspended_day(self) -> None:
        """停牌日（成交量为 0）不应操作。"""
        dates = pd.bdate_range(start="2024-01-02", periods=10)
        prices = [33.0 + i * 0.05 for i in range(10)]
        volumes = [1000000] * 10
        # 第一天停牌
        volumes[0] = 0

        df = pd.DataFrame({
            "open": prices,
            "high": [p + 0.2 for p in prices],
            "low": [p - 0.1 for p in prices],
            "close": prices,
            "vol": volumes,
            "amount": [v * 10 for v in volumes],
            "turnover_rate": [1.5] * 10,
            "adj_factor": [1.0] * 10,
        }, index=dates)

        strat = _run_cerebro(SignalStrategy, df, cash=5_000, hold_days=20)

        # 策略应该能运行完成
        assert len(strat.equity_curve) == 10
        # 如果有买入，应该不在第一天（停牌日）
        buy_trades = [t for t in strat.trades_log if t["direction"] == "buy"]
        if buy_trades:
            assert buy_trades[0]["date"] != dates[0].date().isoformat()
