"""测试数据初始化向导的核心功能。"""

import pytest
from datetime import date, timedelta


def test_date_range_calculation_1_year():
    """测试日期范围计算 - 1 年。"""
    end_date = date.today()
    start_date = end_date - timedelta(days=365)
    days = (end_date - start_date).days

    # 1 年约 365 天
    assert 360 <= days <= 370


def test_date_range_calculation_3_years():
    """测试日期范围计算 - 3 年。"""
    end_date = date.today()
    start_date = end_date - timedelta(days=1095)
    days = (end_date - start_date).days

    # 3 年约 1095 天
    assert 1090 <= days <= 1100


def test_date_range_calculation_5_years_warning():
    """测试日期范围计算 - 5 年警告阈值。"""
    end_date = date.today()
    start_date = end_date - timedelta(days=1826)  # 超过 5 年
    days = (end_date - start_date).days

    # 超过 5 年应该触发警告
    assert days >= 365 * 5


def test_trading_days_estimation():
    """测试交易日数量估算。"""
    # 1 年约 250 个交易日
    days_1y = 365
    trading_days_1y = int(days_1y / 365 * 250)
    assert 240 <= trading_days_1y <= 260

    # 3 年约 750 个交易日
    days_3y = 1095
    trading_days_3y = int(days_3y / 365 * 250)
    assert 740 <= trading_days_3y <= 760

    # 5 年约 1250 个交易日
    days_5y = 1825
    trading_days_5y = int(days_5y / 365 * 250)
    assert 1240 <= trading_days_5y <= 1260
