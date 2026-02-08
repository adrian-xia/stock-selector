"""A 股回测策略基类和通用信号策略。

AStockStrategy：集成涨跌停检查，记录 equity_curve。
SignalStrategy：通用买入/持有/止损逻辑。
"""

import logging
from datetime import datetime

import backtrader as bt

from app.backtest.price_limit import get_limit_pct, is_limit_down, is_limit_up

logger = logging.getLogger(__name__)


class AStockStrategy(bt.Strategy):
    """A 股回测策略基类。

    所有 A 股回测策略继承此类，自动获得：
    - 涨跌停检查（safe_buy / safe_sell）
    - 每日净值记录（equity_curve）
    - 交易日志（trades_log）
    """

    params = (
        ("ts_code", ""),       # 股票代码
        ("stock_name", ""),    # 股票名称（用于 ST 判断）
    )

    def __init__(self) -> None:
        self.equity_curve: list[dict] = []
        self.trades_log: list[dict] = []
        self._limit_pct = get_limit_pct(self.p.ts_code, self.p.stock_name)
        self._buy_bar: dict[str, int] = {}  # data._name -> 买入时的 bar 编号

    def next(self) -> None:
        """每个 bar 调用，记录净值。子类应 super().next() 后实现逻辑。"""
        dt = self.datas[0].datetime.date(0)
        value = self.broker.getvalue()
        self.equity_curve.append({
            "date": dt.isoformat(),
            "value": round(float(value), 2),
        })

    def safe_buy(self, data: bt.feeds.DataBase | None = None, size: int = 0) -> bt.Order | None:
        """涨跌停安全买入。涨停时不下单。"""
        d = data or self.datas[0]
        close = d.close[0]
        # 需要前日收盘价判断涨停
        if len(d) < 2:
            return self.buy(data=d, size=size)
        pre_close = d.close[-1]
        if is_limit_up(close, pre_close, self._limit_pct):
            logger.debug("涨停拦截买入：%s close=%.2f pre=%.2f", self.p.ts_code, close, pre_close)
            return None
        return self.buy(data=d, size=size)

    def safe_sell(self, data: bt.feeds.DataBase | None = None, size: int = 0) -> bt.Order | None:
        """涨跌停安全卖出。跌停时不下单。"""
        d = data or self.datas[0]
        close = d.close[0]
        if len(d) < 2:
            return self.sell(data=d, size=size)
        pre_close = d.close[-1]
        if is_limit_down(close, pre_close, self._limit_pct):
            logger.debug("跌停拦截卖出：%s close=%.2f pre=%.2f", self.p.ts_code, close, pre_close)
            return None
        return self.sell(data=d, size=size)

    def notify_trade(self, trade: bt.Trade) -> None:
        """记录交易日志。"""
        if trade.isclosed:
            self.trades_log.append({
                "stock_code": self.p.ts_code,
                "direction": "sell",
                "date": self.datas[0].datetime.date(0).isoformat(),
                "price": round(float(trade.price), 2),
                "size": abs(int(trade.size)),
                "commission": round(float(trade.commission), 2),
                "pnl": round(float(trade.pnl), 2),
            })
        elif trade.isopen:
            self.trades_log.append({
                "stock_code": self.p.ts_code,
                "direction": "buy",
                "date": self.datas[0].datetime.date(0).isoformat(),
                "price": round(float(trade.price), 2),
                "size": abs(int(trade.size)),
                "commission": round(float(trade.commission), 2),
                "pnl": 0.0,
            })


class SignalStrategy(AStockStrategy):
    """通用信号策略：买入后持有 N 天或止损卖出。

    用于回测选股策略的历史表现。买入条件为首个可交易日，
    卖出条件为持有达到 hold_days 或亏损超过 stop_loss_pct。
    """

    params = (
        ("hold_days", 5),          # 持有天数
        ("stop_loss_pct", 0.05),   # 止损比例（5%）
    )

    def __init__(self) -> None:
        super().__init__()
        self._entry_price: float = 0.0
        self._bars_held: int = 0
        self._in_position: bool = False

    def next(self) -> None:
        """逐 bar 执行买卖逻辑。"""
        super().next()

        # 停牌日不操作
        if self.datas[0].volume[0] <= 0:
            return

        if not self._in_position:
            # 未持仓：尝试买入
            cash = self.broker.getcash()
            price = self.datas[0].close[0]
            if price <= 0:
                return
            # 等权重仓位：全部资金买入，取整到 100 股
            size = int(cash / price / 100) * 100
            if size >= 100:
                order = self.safe_buy(size=size)
                if order:
                    self._entry_price = price
                    self._bars_held = 0
                    self._in_position = True
        else:
            # 已持仓：检查卖出条件
            self._bars_held += 1
            current_price = self.datas[0].close[0]

            # 止损检查
            if self._entry_price > 0:
                loss_pct = (self._entry_price - current_price) / self._entry_price
                if loss_pct >= self.p.stop_loss_pct:
                    order = self.safe_sell(size=self.position.size)
                    if order:
                        self._in_position = False
                    return

            # 持有天数到期
            if self._bars_held >= self.p.hold_days:
                order = self.safe_sell(size=self.position.size)
                if order:
                    self._in_position = False
