"""Trigger 策略：首阴反包。

进攻组信号，强势股弱转强接力。
返回 list[StrategySignal]，含置信度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole, StrategySignal


class FirstNegativeReversalTriggerV2(BaseStrategyV2):
    """首阴反包 Trigger：前日收阴 + 今日阳线反包。"""

    name = "first-negative-reversal-trigger-v2"
    display_name = "首阴反包"
    role = StrategyRole.TRIGGER
    signal_group = SignalGroup.AGGRESSIVE
    description = "强势股首阴后阳线反包，多头重新占优"
    default_params = {
        "min_pct_chg": 2.0,
        "min_vol_ratio": 1.0,
    }
    ai_rating = 7.27  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal]:
        """执行首阴反包检测。

        Returns:
            list[StrategySignal]，命中股票列表
        """
        min_pct_chg = self.params.get("min_pct_chg", 2.0)
        min_vol_ratio = self.params.get("min_vol_ratio", 1.0)

        close = df.get("close", pd.Series(dtype=float)).fillna(0)
        open_ = df.get("open", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)
        close_prev = df.get("close_prev", pd.Series(dtype=float)).fillna(0)

        # 前日收阴
        if "open_prev" in df.columns:
            open_prev = df["open_prev"].fillna(0)
            prev_negative = (close_prev > 0) & (close_prev < open_prev)
        elif "pct_chg_prev" in df.columns:
            pct_chg_prev = df["pct_chg_prev"].fillna(0)
            prev_negative = pct_chg_prev < 0
        else:
            prev_negative = pd.Series(True, index=df.index)

        # 上升趋势 + 今日阳线反包 + 放量
        uptrend = (close > ma20) & (ma20 > 0)
        bullish_today = (close > open_) & (pct_chg >= min_pct_chg)
        reversal = (close_prev > 0) & (close > close_prev)
        volume_ok = vol_ratio >= min_vol_ratio
        trading = vol > 0

        signal_mask = uptrend & prev_negative & bullish_today & reversal & volume_ok & trading

        signals = []
        for ts_code in df.loc[signal_mask, "ts_code"]:
            signals.append(
                StrategySignal(
                    ts_code=ts_code,
                    confidence=1.0,
                )
            )

        return signals
