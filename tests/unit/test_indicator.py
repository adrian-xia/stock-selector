"""技术指标计算引擎的单元测试。

测试 compute_single_stock_indicators() 的各指标计算正确性和边界情况。
"""

from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.data.indicator import compute_single_stock_indicators


def _make_daily_df(
    days: int = 30,
    start_price: float = 10.0,
    start_date: date | None = None,
    prices: list[float] | None = None,
    volumes: list[float] | None = None,
) -> pd.DataFrame:
    """构造测试用的日线 DataFrame。

    Args:
        days: 天数
        start_price: 起始价格
        start_date: 起始日期
        prices: 自定义收盘价列表（覆盖自动生成）
        volumes: 自定义成交量列表

    Returns:
        包含 trade_date, open, high, low, close, vol 的 DataFrame
    """
    if start_date is None:
        start_date = date(2025, 1, 1)

    if prices is not None:
        days = len(prices)
        close_prices = prices
    else:
        # 生成带随机波动的价格序列（固定种子保证可重复）
        rng = np.random.default_rng(42)
        changes = rng.normal(0, 0.02, days)
        close_prices = [start_price]
        for c in changes[1:]:
            close_prices.append(close_prices[-1] * (1 + c))

    if volumes is None:
        rng = np.random.default_rng(42)
        volumes = (rng.uniform(800, 1200, days)).tolist()

    records = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        c = close_prices[i]
        records.append({
            "trade_date": d,
            "open": c * 0.99,
            "high": c * 1.02,
            "low": c * 0.98,
            "close": c,
            "vol": volumes[i],
        })
    return pd.DataFrame(records)


class TestComputeSingleStockIndicators:
    """测试 compute_single_stock_indicators 主函数。"""

    def test_returns_all_indicator_columns(self):
        """验证返回的 DataFrame 包含全部 29 个指标列。"""
        df = _make_daily_df(days=300)
        result = compute_single_stock_indicators(df)

        expected_cols = [
            "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
            "macd_dif", "macd_dea", "macd_hist",
            "kdj_k", "kdj_d", "kdj_j",
            "rsi6", "rsi12", "rsi24",
            "boll_upper", "boll_mid", "boll_lower",
            "vol_ma5", "vol_ma10", "vol_ratio",
            "atr14",
            "wr", "cci", "bias", "obv",
            "donchian_upper", "donchian_lower",
        ]
        for col in expected_cols:
            assert col in result.columns, f"缺少指标列: {col}"

    def test_row_count_unchanged(self):
        """验证行数不变。"""
        df = _make_daily_df(days=100)
        result = compute_single_stock_indicators(df)
        assert len(result) == 100

    def test_original_columns_preserved(self):
        """验证原始列被保留。"""
        df = _make_daily_df(days=30)
        result = compute_single_stock_indicators(df)
        for col in ["trade_date", "open", "high", "low", "close", "vol"]:
            assert col in result.columns


class TestMACalculation:
    """测试简单移动平均线计算。"""

    def test_ma5_value(self):
        """验证 MA5 计算值。"""
        prices = [10.0, 10.5, 11.0, 10.8, 11.2]
        df = _make_daily_df(prices=prices)
        result = compute_single_stock_indicators(df)
        # MA5 = (10.0 + 10.5 + 11.0 + 10.8 + 11.2) / 5 = 10.7
        assert result["ma5"].iloc[-1] == pytest.approx(10.7, abs=0.01)

    def test_ma5_nan_for_insufficient_data(self):
        """验证数据不足时 MA5 前 4 行为 NaN。"""
        df = _make_daily_df(days=10)
        result = compute_single_stock_indicators(df)
        assert pd.isna(result["ma5"].iloc[3])
        assert pd.notna(result["ma5"].iloc[4])

    def test_ma250_nan_for_short_history(self):
        """验证 100 天数据时 MA250 全部为 NaN。"""
        df = _make_daily_df(days=100)
        result = compute_single_stock_indicators(df)
        assert result["ma250"].isna().all()

    def test_ma60_partial_nan(self):
        """验证 MA60 前 59 行为 NaN，第 60 行开始有值。"""
        df = _make_daily_df(days=100)
        result = compute_single_stock_indicators(df)
        assert pd.isna(result["ma60"].iloc[58])
        assert pd.notna(result["ma60"].iloc[59])


class TestMACDCalculation:
    """测试 MACD 指标计算。"""

    def test_macd_columns_exist(self):
        """验证 MACD 三列都存在。"""
        df = _make_daily_df(days=60)
        result = compute_single_stock_indicators(df)
        assert "macd_dif" in result.columns
        assert "macd_dea" in result.columns
        assert "macd_hist" in result.columns

    def test_macd_hist_formula(self):
        """验证 HIST = 2 * (DIF - DEA)。"""
        df = _make_daily_df(days=60)
        result = compute_single_stock_indicators(df)
        # 取最后一行验证公式
        last = result.iloc[-1]
        expected_hist = 2.0 * (last["macd_dif"] - last["macd_dea"])
        assert last["macd_hist"] == pytest.approx(expected_hist, abs=1e-6)


class TestKDJCalculation:
    """测试 KDJ 指标计算。"""

    def test_kdj_columns_exist(self):
        """验证 KDJ 三列都存在。"""
        df = _make_daily_df(days=30)
        result = compute_single_stock_indicators(df)
        assert "kdj_k" in result.columns
        assert "kdj_d" in result.columns
        assert "kdj_j" in result.columns

    def test_kdj_j_formula(self):
        """验证 J = 3K - 2D。"""
        df = _make_daily_df(days=30)
        result = compute_single_stock_indicators(df)
        last = result.iloc[-1]
        expected_j = 3.0 * last["kdj_k"] - 2.0 * last["kdj_d"]
        assert last["kdj_j"] == pytest.approx(expected_j, abs=1e-6)

    def test_kdj_flat_price_no_division_error(self):
        """验证价格不变时不会除零错误。"""
        # 所有价格相同
        prices = [10.0] * 20
        df = _make_daily_df(prices=prices)
        # high == low == close，不应报错
        df["high"] = 10.0
        df["low"] = 10.0
        result = compute_single_stock_indicators(df)
        # RSV 应为 50
        assert pd.notna(result["kdj_k"].iloc[-1])


class TestRSICalculation:
    """测试 RSI 指标计算。"""

    def test_rsi_range(self):
        """验证 RSI 值在 [0, 100] 范围内。"""
        df = _make_daily_df(days=60)
        result = compute_single_stock_indicators(df)
        valid_rsi6 = result["rsi6"].dropna()
        assert (valid_rsi6 >= 0).all()
        assert (valid_rsi6 <= 100).all()

    def test_rsi_all_gains(self):
        """验证单调递增价格的 RSI 为 100。"""
        prices = [10.0 + i * 0.1 for i in range(30)]
        df = _make_daily_df(prices=prices)
        result = compute_single_stock_indicators(df)
        # 全部上涨，RSI 应为 100
        assert result["rsi6"].iloc[-1] == pytest.approx(100.0, abs=0.01)

    def test_rsi6_nan_for_first_rows(self):
        """验证 RSI6 前几行为 NaN。"""
        df = _make_daily_df(days=20)
        result = compute_single_stock_indicators(df)
        # 前 6 行应为 NaN（需要 6 个周期 + 1 个 diff）
        assert pd.isna(result["rsi6"].iloc[0])


class TestBollingerBands:
    """测试布林带指标计算。"""

    def test_boll_order(self):
        """验证 BOLL_UPPER > BOLL_MID > BOLL_LOWER。"""
        df = _make_daily_df(days=60)
        result = compute_single_stock_indicators(df)
        valid = result.dropna(subset=["boll_upper", "boll_mid", "boll_lower"])
        assert (valid["boll_upper"] > valid["boll_mid"]).all()
        assert (valid["boll_mid"] > valid["boll_lower"]).all()

    def test_boll_mid_equals_ma20(self):
        """验证 BOLL_MID 等于 MA20。"""
        df = _make_daily_df(days=60)
        result = compute_single_stock_indicators(df)
        valid = result.dropna(subset=["boll_mid", "ma20"])
        pd.testing.assert_series_equal(
            valid["boll_mid"].reset_index(drop=True),
            valid["ma20"].reset_index(drop=True),
            check_names=False,
        )


class TestVolumeIndicators:
    """测试成交量指标计算。"""

    def test_vol_ratio_value(self):
        """验证量比计算：vol / vol_ma5。"""
        volumes = [1000.0] * 4 + [1500.0]
        df = _make_daily_df(days=5, volumes=volumes)
        result = compute_single_stock_indicators(df)
        # vol_ma5 = (1000*4 + 1500) / 5 = 1100
        # vol_ratio = 1500 / 1100 ≈ 1.3636
        assert result["vol_ratio"].iloc[-1] == pytest.approx(1500.0 / 1100.0, abs=0.01)

    def test_vol_ratio_zero_volume(self):
        """验证 vol_ma5 为 0 时 vol_ratio 为 NaN。"""
        volumes = [0.0] * 10
        df = _make_daily_df(days=10, volumes=volumes)
        result = compute_single_stock_indicators(df)
        assert pd.isna(result["vol_ratio"].iloc[-1])


class TestATR:
    """测试 ATR 指标计算。"""

    def test_atr_non_negative(self):
        """验证 ATR 始终 >= 0。"""
        df = _make_daily_df(days=30)
        result = compute_single_stock_indicators(df)
        valid_atr = result["atr14"].dropna()
        assert (valid_atr >= 0).all()

    def test_atr_nan_for_first_rows(self):
        """验证 ATR14 前几行为 NaN。"""
        df = _make_daily_df(days=20)
        result = compute_single_stock_indicators(df)
        # 第一行没有 prev_close，所以 TR 从第 2 行开始
        assert pd.isna(result["atr14"].iloc[0])


class TestEdgeCases:
    """测试边界情况。"""

    def test_empty_dataframe(self):
        """验证空 DataFrame 输入返回空 DataFrame 且包含指标列。"""
        df = pd.DataFrame(columns=["trade_date", "open", "high", "low", "close", "vol"])
        result = compute_single_stock_indicators(df)
        assert result.empty
        assert "ma5" in result.columns
        assert "rsi6" in result.columns
        assert "atr14" in result.columns

    def test_short_history_new_stock(self):
        """验证新股（仅 10 天数据）不报错，长周期指标为 NaN。"""
        df = _make_daily_df(days=10)
        result = compute_single_stock_indicators(df)
        assert len(result) == 10
        # MA60 应全部为 NaN
        assert result["ma60"].isna().all()
        # MA5 从第 5 行开始有值
        assert pd.notna(result["ma5"].iloc[4])

    def test_suspended_stock_zero_volume(self):
        """验证停牌股（vol=0）不报错。"""
        volumes = [0.0] * 20
        df = _make_daily_df(days=20, volumes=volumes)
        result = compute_single_stock_indicators(df)
        assert len(result) == 20
        # vol_ma5 应为 0，vol_ratio 应为 NaN
        valid_vol_ma5 = result["vol_ma5"].dropna()
        assert (valid_vol_ma5 == 0).all()

    def test_single_row(self):
        """验证仅 1 行数据不报错。"""
        df = _make_daily_df(days=1)
        result = compute_single_stock_indicators(df)
        assert len(result) == 1
        # 所有指标应为 NaN（数据不足）
        assert pd.isna(result["ma5"].iloc[0])


# ============================================================
# 新增指标计算函数测试
# ============================================================

from app.data.indicator import (
    _compute_wr,
    _compute_cci,
    _compute_bias,
    _compute_obv,
    _compute_donchian,
)


class TestComputeWR:
    """测试 Williams %R 计算。"""

    def test_wr_range(self):
        """验证 WR 值在 [-100, 0] 范围内。"""
        df = _make_daily_df(days=30)
        wr = _compute_wr(df["high"], df["low"], df["close"], period=14)
        valid = wr.dropna()
        assert (valid >= -100).all()
        assert (valid <= 0).all()

    def test_wr_nan_for_insufficient_data(self):
        """验证数据不足时 WR 为 NaN。"""
        df = _make_daily_df(days=20)
        wr = _compute_wr(df["high"], df["low"], df["close"], period=14)
        # 前 13 行应为 NaN
        assert pd.isna(wr.iloc[12])
        assert pd.notna(wr.iloc[13])

    def test_wr_flat_price(self):
        """验证价格不变时 WR 为 -50。"""
        prices = [10.0] * 20
        df = _make_daily_df(prices=prices)
        df["high"] = 10.0
        df["low"] = 10.0
        wr = _compute_wr(df["high"], df["low"], df["close"], period=14)
        valid = wr.dropna()
        assert (valid == -50.0).all()

    def test_wr_at_high(self):
        """验证收盘价等于最高价时 WR 为 0。"""
        # 构造收盘价始终等于区间最高价的场景
        prices = list(range(1, 21))  # 单调递增
        df = _make_daily_df(prices=[float(p) for p in prices])
        df["high"] = df["close"]
        df["low"] = df["close"] * 0.9
        wr = _compute_wr(df["high"], df["low"], df["close"], period=14)
        # 最后一行：close == highest_high，WR 应为 0
        assert wr.iloc[-1] == pytest.approx(0.0, abs=0.01)


class TestComputeCCI:
    """测试 CCI 计算。"""

    def test_cci_nan_for_insufficient_data(self):
        """验证数据不足时 CCI 为 NaN。"""
        df = _make_daily_df(days=20)
        cci = _compute_cci(df["high"], df["low"], df["close"], period=14)
        assert pd.isna(cci.iloc[12])
        assert pd.notna(cci.iloc[13])

    def test_cci_flat_price_is_zero(self):
        """验证价格不变时 CCI 为 0（MAD=0 时设为 0）。"""
        prices = [10.0] * 20
        df = _make_daily_df(prices=prices)
        df["high"] = 10.0
        df["low"] = 10.0
        cci = _compute_cci(df["high"], df["low"], df["close"], period=14)
        valid = cci.dropna()
        assert (valid == 0.0).all()

    def test_cci_positive_for_uptrend(self):
        """验证上涨趋势中 CCI 为正。"""
        prices = [10.0 + i * 0.5 for i in range(30)]
        df = _make_daily_df(prices=prices)
        cci = _compute_cci(df["high"], df["low"], df["close"], period=14)
        # 最后几行应为正值
        assert cci.iloc[-1] > 0


class TestComputeBIAS:
    """测试 BIAS 乖离率计算。"""

    def test_bias_zero_when_close_equals_ma(self):
        """验证收盘价等于 MA20 时 BIAS 为 0。"""
        close = pd.Series([10.0] * 5)
        ma20 = pd.Series([10.0] * 5)
        bias = _compute_bias(close, ma20)
        assert (bias == 0.0).all()

    def test_bias_positive_when_above_ma(self):
        """验证收盘价高于 MA20 时 BIAS 为正。"""
        close = pd.Series([11.0])
        ma20 = pd.Series([10.0])
        bias = _compute_bias(close, ma20)
        # (11 - 10) / 10 * 100 = 10.0
        assert bias.iloc[0] == pytest.approx(10.0, abs=0.01)

    def test_bias_negative_when_below_ma(self):
        """验证收盘价低于 MA20 时 BIAS 为负。"""
        close = pd.Series([9.0])
        ma20 = pd.Series([10.0])
        bias = _compute_bias(close, ma20)
        # (9 - 10) / 10 * 100 = -10.0
        assert bias.iloc[0] == pytest.approx(-10.0, abs=0.01)

    def test_bias_nan_when_ma_zero(self):
        """验证 MA20 为 0 时 BIAS 为 NaN。"""
        close = pd.Series([10.0])
        ma20 = pd.Series([0.0])
        bias = _compute_bias(close, ma20)
        assert pd.isna(bias.iloc[0])

    def test_bias_nan_when_ma_nan(self):
        """验证 MA20 为 NaN 时 BIAS 为 NaN。"""
        close = pd.Series([10.0])
        ma20 = pd.Series([np.nan])
        bias = _compute_bias(close, ma20)
        assert pd.isna(bias.iloc[0])


class TestComputeOBV:
    """测试 OBV 能量潮计算。"""

    def test_obv_basic(self):
        """验证 OBV 基本计算逻辑。"""
        close = pd.Series([10.0, 11.0, 10.5, 11.5, 12.0])
        vol = pd.Series([100.0, 200.0, 150.0, 300.0, 250.0])
        obv = _compute_obv(close, vol)
        # day0: 0 (cumsum starts, first diff is NaN → fillna(0))
        # day1: +200 (price up)
        # day2: +200 - 150 = 50 (price down)
        # day3: 50 + 300 = 350 (price up)
        # day4: 350 + 250 = 600 (price up)
        assert obv.iloc[-1] == pytest.approx(600.0, abs=0.01)

    def test_obv_flat_price(self):
        """验证价格不变时 OBV 不变（vol 贡献为 0）。"""
        close = pd.Series([10.0, 10.0, 10.0])
        vol = pd.Series([100.0, 200.0, 300.0])
        obv = _compute_obv(close, vol)
        # 价格不变，direction=0，OBV 始终为 0
        assert obv.iloc[-1] == pytest.approx(0.0, abs=0.01)

    def test_obv_all_down(self):
        """验证单调下跌时 OBV 为负。"""
        close = pd.Series([10.0, 9.0, 8.0, 7.0])
        vol = pd.Series([100.0, 100.0, 100.0, 100.0])
        obv = _compute_obv(close, vol)
        # day0: 0, day1: -100, day2: -200, day3: -300
        assert obv.iloc[-1] == pytest.approx(-300.0, abs=0.01)


class TestComputeDonchian:
    """测试唐奇安通道计算。"""

    def test_donchian_nan_for_insufficient_data(self):
        """验证数据不足时唐奇安通道为 NaN。"""
        df = _make_daily_df(days=25)
        upper, lower = _compute_donchian(df["high"], df["low"], period=20)
        # shift(1) + rolling(20) 需要 21 行数据
        assert pd.isna(upper.iloc[19])
        assert pd.notna(upper.iloc[20])

    def test_donchian_excludes_current_day(self):
        """验证唐奇安通道不含当日数据。"""
        # 构造最后一天 high 特别高的数据
        prices = [10.0] * 24 + [20.0]
        df = _make_daily_df(prices=prices)
        upper, lower = _compute_donchian(df["high"], df["low"], period=20)
        # 最后一行的 upper 不应包含当日的 high（20*1.02）
        # 应该是前 20 天的最高价 = 10.0 * 1.02
        assert upper.iloc[-1] == pytest.approx(10.0 * 1.02, abs=0.1)

    def test_donchian_upper_gte_lower(self):
        """验证 upper >= lower。"""
        df = _make_daily_df(days=30)
        upper, lower = _compute_donchian(df["high"], df["low"], period=20)
        valid = upper.dropna() >= lower.dropna()
        assert valid.all()
