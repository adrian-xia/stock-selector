"""测试涨跌停检查器。

覆盖各板块涨跌停判断：主板、创业板、科创板、ST。
"""

import pytest

from app.backtest.price_limit import get_limit_pct, is_limit_down, is_limit_up


class TestGetLimitPct:
    """测试涨跌停幅度获取。"""

    def test_main_board_sh(self) -> None:
        """主板（上海 600xxx）应返回 10%。"""
        assert get_limit_pct("600519.SH") == 0.10

    def test_main_board_sz(self) -> None:
        """主板（深圳 000xxx）应返回 10%。"""
        assert get_limit_pct("000858.SZ") == 0.10

    def test_chinext(self) -> None:
        """创业板（300xxx）应返回 20%。"""
        assert get_limit_pct("300750.SZ") == 0.20

    def test_star_market(self) -> None:
        """科创板（688xxx）应返回 20%。"""
        assert get_limit_pct("688981.SH") == 0.20

    def test_st_stock(self) -> None:
        """ST 股票应返回 5%。"""
        assert get_limit_pct("600000.SH", "ST 某某") == 0.05

    def test_st_star_stock(self) -> None:
        """*ST 股票应返回 5%。"""
        assert get_limit_pct("300001.SZ", "*ST某某") == 0.05

    def test_st_takes_priority(self) -> None:
        """ST 判断优先于板块判断。"""
        # 创业板 ST 股票应返回 5% 而非 20%
        assert get_limit_pct("300001.SZ", "ST创业") == 0.05

    def test_no_name_main_board(self) -> None:
        """无名称时按代码判断。"""
        assert get_limit_pct("601318.SH", "") == 0.10

    def test_code_without_suffix(self) -> None:
        """纯数字代码也能正确判断。"""
        assert get_limit_pct("300750") == 0.20


class TestIsLimitUp:
    """测试涨停判断。"""

    def test_exact_limit_up(self) -> None:
        """精确涨停价应判定为涨停。"""
        # 前收 10.00，涨停价 11.00
        assert is_limit_up(11.00, 10.00, 0.10) is True

    def test_near_limit_up(self) -> None:
        """接近涨停价（差 0.01 以内）应判定为涨停。"""
        assert is_limit_up(10.99, 10.00, 0.10) is True

    def test_below_limit_up(self) -> None:
        """低于涨停价应判定为非涨停。"""
        assert is_limit_up(10.50, 10.00, 0.10) is False

    def test_chinext_limit_up(self) -> None:
        """创业板 20% 涨停。"""
        assert is_limit_up(12.00, 10.00, 0.20) is True

    def test_pre_close_zero(self) -> None:
        """前收为 0 时返回 False。"""
        assert is_limit_up(10.00, 0, 0.10) is False

    def test_rounding_case(self) -> None:
        """四舍五入边界情况：前收 9.99，涨停价 10.989 → 10.99。"""
        assert is_limit_up(10.98, 9.99, 0.10) is True


class TestIsLimitDown:
    """测试跌停判断。"""

    def test_exact_limit_down(self) -> None:
        """精确跌停价应判定为跌停。"""
        # 前收 10.00，跌停价 9.00
        assert is_limit_down(9.00, 10.00, 0.10) is True

    def test_near_limit_down(self) -> None:
        """接近跌停价（差 0.01 以内）应判定为跌停。"""
        assert is_limit_down(9.01, 10.00, 0.10) is True

    def test_above_limit_down(self) -> None:
        """高于跌停价应判定为非跌停。"""
        assert is_limit_down(9.50, 10.00, 0.10) is False

    def test_chinext_limit_down(self) -> None:
        """创业板 20% 跌停。"""
        assert is_limit_down(8.00, 10.00, 0.20) is True

    def test_pre_close_zero(self) -> None:
        """前收为 0 时返回 False。"""
        assert is_limit_down(10.00, 0, 0.10) is False

    def test_st_limit_down(self) -> None:
        """ST 股票 5% 跌停。"""
        # 前收 10.00，跌停价 9.50
        assert is_limit_down(9.50, 10.00, 0.05) is True
        assert is_limit_down(9.60, 10.00, 0.05) is False
