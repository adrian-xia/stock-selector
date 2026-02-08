"""A 股佣金模型。

费用结构：
- 佣金：买卖双向万 2.5，最低 5 元
- 印花税：卖出千 1（买入不收）
- 过户费：忽略
"""

import backtrader as bt


class ChinaStockCommission(bt.CommInfoBase):
    """A 股交易佣金模型。

    继承 Backtrader 的 CommInfoBase，实现 A 股特有的费用计算：
    佣金万 2.5（最低 5 元）+ 卖出印花税千 1。
    """

    params = (
        ("commission", 0.025),         # 佣金费率：万 2.5（Backtrader COMM_PERC 模式会 /100）
        ("stamp_duty", 0.001),         # 印花税费率：千 1
        ("min_commission", 5.0),       # 最低佣金：5 元
        ("stocklike", True),           # 股票模式
        ("commtype", bt.CommInfoBase.COMM_PERC),  # 百分比佣金
    )

    def _getcommission(
        self,
        size: float,
        price: float,
        pseudoexec: bool,
    ) -> float:
        """计算交易佣金。

        Args:
            size: 交易数量（正数买入，负数卖出）
            price: 成交价格
            pseudoexec: 是否为模拟执行

        Returns:
            佣金金额
        """
        turnover = abs(size) * price

        # 佣金（买卖双向），最低 5 元
        commission = max(turnover * self.p.commission, self.p.min_commission)

        # 印花税（仅卖出）
        stamp_duty = 0.0
        if size < 0:  # 卖出
            stamp_duty = turnover * self.p.stamp_duty

        return commission + stamp_duty
