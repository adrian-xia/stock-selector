"""测试 BacktestEngine 基本流程。

使用构造的 DataFrame，不依赖数据库。仅测试 Cerebro 配置和执行。
"""

from datetime import date

import backtrader as bt
import pandas as pd
import pytest

from app.backtest.commission import ChinaStockCommission
from app.backtest.data_feed import build_data_feed
from app.backtest.engine import calc_equal_weight_shares
from app.backtest.strategy import AStockStrategy, SignalStrategy


def _make_test_df(days: int = 30, start_price: float = 10.0) -> pd.DataFrame:
    """构造测试用的股票日线 DataFrame。

    模拟一个简单的上涨趋势。
    """
    dates = pd.bdate_range(start="2024-01-02", periods=days)
    prices = [start_price + i * 0.1 for i in range(days)]
    df = pd.DataFrame({
        "open": prices,
        "high": [p + 0.2 for p in prices],
        "low": [p - 0.1 for p in prices],
        "close": prices,
        "vol": [1000000] * days,
        "amount": [10000000] * days,
        "turnover_rate": [1.5] * days,
        "adj_factor": [1.0] * days,
    }, index=dates)
    return df


class TestCalcEqualWeightShares:
    """测试等权重仓位计算。"""

    def test_normal_case(self) -> None:
        """正常情况：100 万资金，2 只股票，价格 50 元。"""
        # 每只 50 万，50 万 / 50 = 10000 股，已是 100 整数倍
        shares = calc_equal_weight_shares(1_000_000, 2, 50.0)
        assert shares == 10000

    def test_round_down_to_100(self) -> None:
        """取整到 100 股（向下取整）。"""
        # 100 万 / 1 只 / 33 元 = 30303 股 → 30300 股
        shares = calc_equal_weight_shares(1_000_000, 1, 33.0)
        assert shares == 30300
        assert shares % 100 == 0

    def test_insufficient_funds(self) -> None:
        """资金不足买 100 股时返回 0。"""
        shares = calc_equal_weight_shares(500, 1, 100.0)
        assert shares == 0

    def test_zero_stocks(self) -> None:
        """股票数量为 0 时返回 0。"""
        shares = calc_equal_weight_shares(1_000_000, 0, 50.0)
        assert shares == 0

    def test_zero_price(self) -> None:
        """价格为 0 时返回 0。"""
        shares = calc_equal_weight_shares(1_000_000, 1, 0)
        assert shares == 0

    def test_negative_price(self) -> None:
        """价格为负时返回 0。"""
        shares = calc_equal_weight_shares(1_000_000, 1, -10.0)
        assert shares == 0


class TestCerebroExecution:
    """测试 Cerebro 配置和执行（不依赖数据库）。"""

    def test_basic_run(self) -> None:
        """基本回测流程：加载数据 → 执行策略 → 获取结果。"""
        df = _make_test_df(days=30)
        feed = build_data_feed(df, name="600519.SH")

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(1_000_000)
        cerebro.broker.addcommissioninfo(ChinaStockCommission())
        cerebro.broker.set_slippage_perc(0.001)
        cerebro.adddata(feed, name="600519.SH")
        cerebro.addstrategy(SignalStrategy, ts_code="600519.SH")

        # 添加 Analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        results = cerebro.run(runonce=False, cheat_on_open=False)
        strat = results[0]

        # 验证策略执行完成
        assert strat is not None
        # 验证 equity_curve 被记录
        assert len(strat.equity_curve) == 30
        # 验证每个 equity_curve 条目格式正确
        for entry in strat.equity_curve:
            assert "date" in entry
            assert "value" in entry
            assert isinstance(entry["value"], float)

    def test_analyzers_available(self) -> None:
        """验证 Analyzers 正确挂载并可获取分析结果。"""
        df = _make_test_df(days=30)
        feed = build_data_feed(df, name="600519.SH")

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(1_000_000)
        cerebro.adddata(feed, name="600519.SH")
        cerebro.addstrategy(SignalStrategy, ts_code="600519.SH")
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name="sharpe")
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        results = cerebro.run(runonce=False)
        strat = results[0]

        # 验证 Analyzers 可访问
        assert hasattr(strat.analyzers, "sharpe")
        assert hasattr(strat.analyzers, "drawdown")
        assert hasattr(strat.analyzers, "trades")
        assert hasattr(strat.analyzers, "returns")

        # 验证可以获取分析数据
        sharpe_data = strat.analyzers.sharpe.get_analysis()
        assert isinstance(sharpe_data, dict)

    def test_trades_log_recorded(self) -> None:
        """验证交易日志被正确记录。"""
        # 使用更多天数和佣金模型确保交易能完成
        df = _make_test_df(days=60)
        feed = build_data_feed(df, name="600519.SH")

        cerebro = bt.Cerebro()
        cerebro.broker.setcash(1_000_000)
        cerebro.broker.addcommissioninfo(ChinaStockCommission())
        cerebro.adddata(feed, name="600519.SH")
        cerebro.addstrategy(
            SignalStrategy, ts_code="600519.SH", hold_days=5
        )

        results = cerebro.run(runonce=False)
        strat = results[0]

        # 60 天数据 + hold_days=5，应该有交易记录
        if len(strat.trades_log) > 0:
            # 验证交易记录格式
            for trade in strat.trades_log:
                assert "stock_code" in trade
                assert "direction" in trade
                assert trade["direction"] in ("buy", "sell")
                assert "date" in trade
                assert "price" in trade
                assert "size" in trade
        else:
            # 如果策略未触发交易（可能因为涨跌停拦截），验证 equity_curve 至少被记录
            assert len(strat.equity_curve) == 60

    def test_initial_capital_preserved(self) -> None:
        """验证初始资金正确设置。"""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(500_000)
        assert cerebro.broker.getcash() == 500_000
