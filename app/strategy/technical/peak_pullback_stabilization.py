"""高位回落企稳策略（v1.2）。

逻辑：前期主升浪后高位回落，近期缩量企稳，今日放量小阳二次启动。
核心原则：Layer C 全部使用截面均线关系，彻底避免跨日计算陷阱。

默认参数：
    min_pullback_pct=10.0, max_pullback_pct=35.0
    max_vol_ratio=0.8, ma5_band=0.025
    min_signal_vol_ratio=1.2
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategy


class PeakPullbackStabilizationStrategy(BaseStrategy):
    """高位回落企稳策略：主升浪后深度调整，缩量企稳后放量小阳二次启动。"""

    name = "peak-pullback-stabilization"
    display_name = "高位回落企稳"
    category = "technical"
    description = "前期主升浪后高位回落，缩量企稳后放量小阳二次启动"
    default_params = {
        # Layer A：前期主升浪
        "min_peak_rise_pct": 20.0,   # high_60 距 MA60 的最小乖离率 %
        "ma_tolerance": 0.03,        # 允许当前价略低于 MA60 的容忍偏差
        # Layer B：高位回落
        "min_pullback_pct": 10.0,    # 最小回落幅度 %（距 60 日高点）
        "max_pullback_pct": 35.0,    # 最大回落幅度 %（距 60 日高点）
        # Layer C：缩量企稳（纯截面，无跨日计算）
        "max_vol_ratio": 0.8,        # vol_ma5 / vol_ma10 上限（近期缩量）
        "ma5_band": 0.025,           # 价格距 MA5 的最大偏离率（横盘企稳）
        # Layer D：今日放量启动
        "min_pct_chg": 0.5,          # 启动日最小涨幅 %
        "max_pct_chg": 7.0,          # 启动日最大涨幅 %（排除涨停追高）
        "min_signal_vol_ratio": 1.2, # 启动日最小量比（有效放量）
    }

    async def filter_batch(self, df: pd.DataFrame, target_date: date) -> pd.Series:
        p = self.params

        close     = df.get("close",    pd.Series(dtype=float)).astype(float).fillna(0)
        open_     = df.get("open",     pd.Series(dtype=float)).astype(float).fillna(0)
        vol       = df.get("vol",      pd.Series(dtype=float)).astype(float).fillna(0)
        pct_chg   = df.get("pct_chg",  pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ratio = df.get("vol_ratio",pd.Series(dtype=float)).astype(float).fillna(0)
        ma5       = df.get("ma5",      pd.Series(dtype=float)).astype(float).fillna(0)
        ma5_prev  = df.get("ma5_prev", pd.Series(dtype=float)).astype(float).fillna(0)
        ma20      = df.get("ma20",     pd.Series(dtype=float)).astype(float).fillna(0)
        ma60      = df.get("ma60",     pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ma5   = df.get("vol_ma5",  pd.Series(dtype=float)).astype(float).fillna(0)
        vol_ma10  = df.get("vol_ma10", pd.Series(dtype=float)).astype(float).fillna(0)

        # high_60：60 日最高价，暂用 high_20 * 1.1 降级（P1 补充预计算后移除）
        if "high_60" in df.columns:
            high_60 = df["high_60"].astype(float).fillna(0)
        elif "high_20" in df.columns:
            high_60 = df["high_20"].astype(float).fillna(0) * 1.1
        else:
            high_60 = close * 1.25

        # 回落幅度 = (60日高点 - 今收) / 60日高点
        pullback_pct = (high_60 - close) / high_60.replace(0, float("nan")) * 100
        pullback_pct = pullback_pct.fillna(0)

        # ── Layer A：前期主升浪（high_60 显著高于 MA60）──────────
        layer_a = (
            (high_60 > 0) &
            (high_60 > ma60 * (1 + p["min_peak_rise_pct"] / 100.0)) &
            (close >= ma60 * (1 - p["ma_tolerance"])) &
            (vol > 0)
        )

        # ── Layer B：高位回落确认 ─────────────────────────────────
        layer_b = (
            (pullback_pct >= p["min_pullback_pct"]) &
            (pullback_pct <= p["max_pullback_pct"]) &
            (close < ma20)
        )

        # ── Layer C：缩量企稳（纯截面，无跨日计算）──────────────
        # C1: vol_ma5 < vol_ma10 * threshold → 近期5日均量显著低于10日均量
        vol_ma10_safe = vol_ma10.replace(0, float("nan"))
        recent_shrink = (vol_ma5 < vol_ma10_safe * p["max_vol_ratio"]).fillna(False)

        # C2: 价格紧贴 MA5（偏离 < ma5_band）→ 跌势趋缓，横盘构筑平台
        ma5_safe = ma5.replace(0, float("nan"))
        price_stable = ((close - ma5_safe).abs() / ma5_safe < p["ma5_band"]).fillna(False)

        # C3: MA5 不再下行 → 短期均线走平或上翘，防持续阴跌
        ma5_rising = (ma5_prev > 0) & (ma5 >= ma5_prev)

        layer_c = recent_shrink & price_stable & ma5_rising & (pct_chg > -9.5)

        # ── Layer D：今日放量小阳启动 ─────────────────────────────
        layer_d = (
            (close > open_) &
            (pct_chg >= p["min_pct_chg"]) &
            (pct_chg <= p["max_pct_chg"]) &
            (vol_ratio >= p["min_signal_vol_ratio"])
        )

        return layer_a & layer_b & layer_c & layer_d
