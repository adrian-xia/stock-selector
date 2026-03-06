"""Confirmer 策略：RSI 超卖回升。

仅在 MA20 向上时启用，为底部信号 +0.2 加分。
返回加分系数 0.0-1.0。
"""

from datetime import date

import pandas as pd

from app.strategy.base import BaseStrategyV2, StrategyRole


class RSIOversoldConfirmerV2(BaseStrategyV2):
    """RSI 超卖回升 Confirmer：底部反弹确认。"""

    name = "rsi-oversold-confirmer-v2"
    display_name = "RSI 超卖回升（确认）"
    role = StrategyRole.CONFIRMER
    signal_group = None
    description = "RSI 从超卖区回升，仅 MA20 向上时启用，为底部信号加分"
    default_params = {
        "period": 6,
        "oversold": 20,
        "bounce": 30,
    }
    ai_rating = 5.58  # 三模型均分

    async def execute(
        self,
        df: pd.DataFrame,
        target_date: date,
    ) -> pd.Series:
        """执行确认检查。

        Returns:
            pd.Series[float]，索引为 ts_code，加分系数 0.0-1.0
        """
        period = self.params.get("period", 6)
        oversold = self.params.get("oversold", 20)
        bounce = self.params.get("bounce", 30)

        # 根据 period 选择 RSI 列
        rsi_col = f"rsi{period}"
        rsi = df.get(rsi_col, pd.Series(dtype=float))
        rsi_prev = df.get(f"{rsi_col}_prev", pd.Series(dtype=float))

        # MA20 向上趋势判断
        ma20 = df.get("ma20", pd.Series(dtype=float))
        ma20_prev = df.get("ma20_prev", pd.Series(dtype=float))
        ma20_up = (ma20.notna() & ma20_prev.notna() & (ma20 > ma20_prev))

        # RSI 从超卖区回升
        rsi_signal = (
            rsi.notna()
            & rsi_prev.notna()
            & (rsi_prev < oversold)  # 前日超卖
            & (rsi > bounce)  # 当日回升
        )

        # 仅在 MA20 向上时启用
        confirmed = rsi_signal & ma20_up

        result = confirmed.astype(float)

        # 确保索引是 ts_code
        if "ts_code" in df.columns:
            result.index = df["ts_code"].values

        return result
