"""回测执行引擎：Cerebro 配置、数据加载、策略执行。

BacktestEngine 封装 Backtrader 的 Cerebro，配置 A 股佣金、滑点、
Analyzers，加载数据并执行回测。
"""

import asyncio
import logging
import math
import time
from datetime import date
from typing import Any

import backtrader as bt
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.backtest.commission import ChinaStockCommission
from app.backtest.data_feed import build_data_feed, load_stock_data
from app.backtest.strategy import SignalStrategy

logger = logging.getLogger(__name__)


class BacktestEngine:
    """回测执行引擎。

    配置 Cerebro，加载数据，执行回测，返回结果。
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self._session_factory = session_factory

    async def _load_data(
        self,
        stock_codes: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, Any]:
        """异步加载所有股票数据。"""
        data_frames = {}
        async with self._session_factory() as session:
            for code in stock_codes:
                df = await load_stock_data(session, code, start_date, end_date)
                if not df.empty:
                    data_frames[code] = df
                else:
                    logger.warning("股票 %s 无数据，跳过", code)
        return data_frames

    def _run_cerebro(
        self,
        data_frames: dict[str, Any],
        strategy_params: dict,
        initial_capital: float,
    ) -> list:
        """同步执行 Backtrader Cerebro。"""
        cerebro = bt.Cerebro()

        # 资金配置
        cerebro.broker.setcash(initial_capital)

        # A 股佣金模型
        cerebro.broker.addcommissioninfo(ChinaStockCommission())

        # 滑点：千 1
        cerebro.broker.set_slippage_perc(0.001)

        # 添加数据
        for code, df in data_frames.items():
            feed = build_data_feed(df, name=code)
            cerebro.adddata(feed, name=code)

        # 添加策略
        ts_code = list(data_frames.keys())[0] if data_frames else ""
        cerebro.addstrategy(
            SignalStrategy,
            ts_code=ts_code,
            **strategy_params,
        )

        # 添加 Analyzers
        cerebro.addanalyzer(
            bt.analyzers.SharpeRatio,
            _name="sharpe",
            timeframe=bt.TimeFrame.Days,
            annualize=True,
        )
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name="drawdown")
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name="trades")
        cerebro.addanalyzer(bt.analyzers.Returns, _name="returns")

        # 执行回测（防未来函数）
        results = cerebro.run(runonce=False, cheat_on_open=False)
        return results

    async def run(
        self,
        stock_codes: list[str],
        strategy_name: str,
        strategy_params: dict,
        start_date: date,
        end_date: date,
        initial_capital: float = 1_000_000.0,
    ) -> dict[str, Any]:
        """执行完整回测流程。

        Args:
            stock_codes: 股票代码列表
            strategy_name: 策略名称
            strategy_params: 策略参数
            start_date: 回测开始日期
            end_date: 回测结束日期
            initial_capital: 初始资金

        Returns:
            包含绩效指标、交易记录和净值曲线的字典
        """
        start_time = time.monotonic()

        # 异步加载数据
        data_frames = await self._load_data(stock_codes, start_date, end_date)
        if not data_frames:
            raise ValueError(f"所有股票在 {start_date} ~ {end_date} 均无数据")

        # 在线程池中执行同步的 Backtrader
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            self._run_cerebro,
            data_frames,
            strategy_params,
            initial_capital,
        )

        strat = results[0]
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return {
            "strategy_instance": strat,
            "equity_curve": strat.equity_curve,
            "trades_log": strat.trades_log,
            "initial_capital": initial_capital,
            "elapsed_ms": elapsed_ms,
        }


def calc_equal_weight_shares(
    cash: float,
    n_stocks: int,
    price: float,
) -> int:
    """计算等权重仓位（取整到 100 股）。

    Args:
        cash: 可用资金
        n_stocks: 股票数量
        price: 当前价格

    Returns:
        买入股数（100 的整数倍）
    """
    if n_stocks <= 0 or price <= 0:
        return 0
    per_stock_cash = cash / n_stocks
    shares = math.floor(per_stock_cash / price / 100) * 100
    return max(shares, 0)


async def run_backtest(
    session_factory: async_sessionmaker,
    stock_codes: list[str],
    strategy_name: str,
    strategy_params: dict,
    start_date: date,
    end_date: date,
    initial_capital: float = 1_000_000.0,
) -> dict[str, Any]:
    """异步回测入口函数。

    封装 BacktestEngine，供 API 层调用。
    """
    engine = BacktestEngine(session_factory)
    return await engine.run(
        stock_codes=stock_codes,
        strategy_name=strategy_name,
        strategy_params=strategy_params,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
    )
