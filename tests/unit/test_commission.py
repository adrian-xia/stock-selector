"""测试 A 股佣金模型。

覆盖买入佣金、卖出佣金（含印花税）、最低佣金。
"""

import pytest

from app.backtest.commission import ChinaStockCommission


@pytest.fixture
def comm() -> ChinaStockCommission:
    """创建佣金模型实例。"""
    return ChinaStockCommission()


class TestChinaStockCommission:
    """测试 A 股佣金计算。"""

    def test_buy_commission_normal(self, comm: ChinaStockCommission) -> None:
        """买入佣金：成交额 * 万 2.5，无印花税。"""
        # 买入 1000 股 @ 10 元 = 10000 元，佣金 = 10000 * 0.00025 = 2.5 → 最低 5 元
        fee = comm._getcommission(1000, 10.0, False)
        assert fee == 5.0  # 最低佣金

    def test_buy_commission_large(self, comm: ChinaStockCommission) -> None:
        """大额买入佣金超过最低值。"""
        # 买入 10000 股 @ 100 元 = 1000000 元，佣金 = 1000000 * 0.00025 = 250 元
        fee = comm._getcommission(10000, 100.0, False)
        assert fee == 250.0

    def test_sell_commission_with_stamp_duty(
        self, comm: ChinaStockCommission
    ) -> None:
        """卖出佣金：佣金 + 印花税。"""
        # 卖出 10000 股 @ 100 元 = 1000000 元
        # 佣金 = 1000000 * 0.00025 = 250 元
        # 印花税 = 1000000 * 0.001 = 1000 元
        # 总计 = 1250 元
        fee = comm._getcommission(-10000, 100.0, False)
        assert fee == 1250.0

    def test_sell_min_commission_with_stamp_duty(
        self, comm: ChinaStockCommission
    ) -> None:
        """小额卖出：最低佣金 + 印花税。"""
        # 卖出 100 股 @ 10 元 = 1000 元
        # 佣金 = max(1000 * 0.00025, 5) = 5 元
        # 印花税 = 1000 * 0.001 = 1 元
        # 总计 = 6 元
        fee = comm._getcommission(-100, 10.0, False)
        assert fee == 6.0

    def test_buy_no_stamp_duty(self, comm: ChinaStockCommission) -> None:
        """买入不收印花税。"""
        # 买入 10000 股 @ 100 元 = 1000000 元
        # 仅佣金 250 元，无印花税
        buy_fee = comm._getcommission(10000, 100.0, False)
        sell_fee = comm._getcommission(-10000, 100.0, False)
        # 卖出比买入多出印花税部分
        assert sell_fee - buy_fee == pytest.approx(1000.0)

    def test_pseudoexec_same_result(
        self, comm: ChinaStockCommission
    ) -> None:
        """模拟执行和实际执行佣金相同。"""
        real = comm._getcommission(1000, 50.0, False)
        pseudo = comm._getcommission(1000, 50.0, True)
        assert real == pseudo
