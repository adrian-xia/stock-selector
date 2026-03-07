"""Trigger 策略：后量超前量。

进攻组信号，资金加速流入确认。
返回 list[StrategySignal]，含置信度。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, SignalGroup, StrategyRole, StrategySignal


class VolumeSurgeContinuationTriggerV2(BaseStrategyV2):
    """后量超前量 Trigger：今日放量 + 量能持续放大 + 上升趋势。"""

    name = "volume-surge-continuation-trigger-v2"
    display_name = "后量超前量"
    role = StrategyRole.TRIGGER
    signal_group = SignalGroup.AGGRESSIVE
    description = "资金加速流入，量能持续放大的趋势加速信号"
    default_params = {
        "surge_ratio": 2.0,
        "vol_ma_ratio": 1.2,
        "min_pct_chg": 1.0,
    }
    ai_rating = 6.93  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> list[StrategySignal]:
        """执行后量超前量检测。

        Returns:
            list[StrategySignal]，命中股票列表
        """
        surge_ratio = self.params.get("surge_ratio", 2.0)
        vol_ma_ratio = self.params.get("vol_ma_ratio", 1.2)
        min_pct_chg = self.params.get("min_pct_chg", 1.0)

        ma5 = df.get("ma5", pd.Series(dtype=float)).fillna(0)
        ma20 = df.get("ma20", pd.Series(dtype=float)).fillna(0)
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)
        vol_ma5 = df.get("vol_ma5", pd.Series(dtype=float)).fillna(0)
        vol_ma10 = df.get("vol_ma10", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)

        surge = vol_ratio >= surge_ratio
        # 后量超前量：vol_ma5 / vol_ma10 >= vol_ma_ratio
        vol_acceleration = (vol_ma10 > 0) & (
            vol_ma5 / vol_ma10.replace(0, float("nan")).fillna(1) >= vol_ma_ratio
        )
        gain = pct_chg >= min_pct_chg
        uptrend = (ma5 > ma20) & (ma20 > 0)
        trading = vol > 0

        signal_mask = surge & vol_acceleration & gain & uptrend & trading

        signals = []
        for ts_code in df.loc[signal_mask, "ts_code"]:
            signals.append(
                StrategySignal(
                    ts_code=ts_code,
                    confidence=1.0,
                )
            )

        return signals
