"""Trigger 策略：放量突破。

进攻组信号，价格创新高 + 量比 >= 2.0。
返回 list[StrategySignal]，含置信度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole, StrategySignal


class VolumeBreakoutTriggerV2(BaseStrategyV2):
    """放量突破 Trigger：创新高 + 放量。"""

    name = "volume-breakout-trigger-v2"
    display_name = "放量突破"
    role = StrategyRole.TRIGGER
    signal_group = SignalGroup.AGGRESSIVE
    description = "价格创近期新高且成交量显著放大"
    default_params = {
        "high_period": 20,
        "min_vol_ratio": 2.0,
    }
    ai_rating = 7.60  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal]:
        """执行放量突破检测。

        Returns:
            list[StrategySignal]，命中股票列表
        """
        min_vol_ratio = self.params.get("min_vol_ratio", 2.0)

        cur_close = df.get("close", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)

        # 优先使用 high_20 列，否则用 ma20 近似
        if "high_20" in df.columns:
            price_breakout = cur_close >= df["high_20"].fillna(float("inf"))
        else:
            ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
            price_breakout = (ma20 > 0) & (cur_close > ma20 * 1.05)

        volume_ok = vol_ratio >= min_vol_ratio
        trading = df.get("vol", pd.Series(dtype=float)).fillna(0) > 0

        signal_mask = price_breakout & volume_ok & trading

        signals = []
        for ts_code in df.loc[signal_mask, "ts_code"]:
            signals.append(
                StrategySignal(
                    ts_code=ts_code,
                    confidence=1.0,
                )
            )

        return signals
