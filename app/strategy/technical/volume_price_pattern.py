"""量价配合策略：放量突破 + 缩量回踩企稳。

第 35 个策略，与现有 34 个策略共存于 Pipeline。
核心区别：需要通过观察池做多日状态追踪。
"""

import logging
from datetime import date

import pandas as pd
from sqlalchemy import text

from app.strategy.base import BaseStrategy

logger = logging.getLogger(__name__)

DEFAULT_PARAMS = {
    "accumulation_days": 60,
    "max_accumulation_range": 0.20,
    "min_t0_pct_chg": 6.0,
    "min_t0_vol_ratio": 2.5,
    "min_washout_days": 3,
    "max_washout_days": 8,
    "max_vol_shrink_ratio": 0.40,
    "price_floor": "t0_open",
    "max_tk_amplitude": 3.0,
    "ma_support_tolerance": 0.015,
    "support_ma_periods": [10, 20],
    "market_index": "000300.SH",
    "market_filter_enabled": True,
    "sector_filter_enabled": True,
    "sector_top_pct": 0.20,
    "sector_momentum_days": 5,
    "watchpool_max_size": 200,
    "watchpool_expire_days": 12,
}


class VolumePricePatternStrategy(BaseStrategy):
    """量价配合（龙回头）策略。"""

    name = "volume-price-pattern"
    display_name = "量价配合（龙回头）"
    category = "technical"
    description = "放量突破后缩量回踩企稳，捕捉主升浪启动点"
    default_params = DEFAULT_PARAMS

    async def filter_batch(
        self, df: pd.DataFrame, target_date: date
    ) -> pd.Series:
        from app.database import async_session_factory
        from app.strategy.filters.market_filter import MarketState, evaluate_market
        from app.strategy.filters.sector_filter import get_strong_sectors
        from app.strategy.watchpool import manager as wpm

        result = pd.Series(False, index=df.index)

        async with async_session_factory() as session:
            # Step 1: 大盘环境检查
            if self.params.get("market_filter_enabled", True):
                state = await evaluate_market(
                    session, target_date, self.params.get("market_index", "000300.SH")
                )
                if state == MarketState.BEARISH:
                    logger.info("[volume-price-pattern] 大盘熔断，跳过")
                    return result

            # Step 2: 扫描新 T0 事件
            t0_mask = self._detect_t0(df)
            if t0_mask.any():
                t0_df = df.loc[t0_mask, ["ts_code", "close", "open", "low", "vol", "pct_chg"]]
                codes = t0_df["ts_code"].tolist()
                valid = await wpm.verify_accumulation(session, codes, target_date, self.params)
                if valid:
                    entries = []
                    for _, row in t0_df.iterrows():
                        if row["ts_code"] in valid:
                            entries.append({
                                "ts_code": row["ts_code"],
                                "strategy_name": self.name,
                                "t0_date": target_date,
                                "t0_close": float(row["close"]),
                                "t0_open": float(row["open"]),
                                "t0_low": float(row["low"]),
                                "t0_volume": int(row["vol"]),
                                "t0_pct_chg": float(row["pct_chg"]),
                                "sector_score": None,
                                "market_score": None,
                            })
                    if entries:
                        n = await wpm.insert_t0_batch(session, entries)
                        logger.info("[volume-price-pattern] 新增 %d 个 T0 事件", n)

            # Step 3: 更新观察池状态
            stats = await wpm.update_watchpool(session, target_date, self.params)
            logger.info("[volume-price-pattern] 观察池更新: %s", stats)

            # Step 4: 检测 Tk 企稳
            triggered_codes = await wpm.check_stabilization(session, target_date, self.params)

            # Step 5: 行业共振（记录得分，不过滤）
            if self.params.get("sector_filter_enabled") and triggered_codes:
                strong = await get_strong_sectors(
                    session, target_date,
                    self.params.get("sector_top_pct", 0.20),
                    self.params.get("sector_momentum_days", 5),
                )
                if strong:
                    # 更新板块得分
                    from app.models.strategy import StrategyWatchpool  # noqa: avoid circular
                    for code in triggered_codes:
                        score = 1.0 if code in strong else 0.0
                        await session.execute(text(
                            "UPDATE strategy_watchpool SET sector_score=:s "
                            "WHERE ts_code=:c AND status='triggered' AND triggered_date=:d"
                        ), {"s": score, "c": code, "d": target_date})

            await session.commit()

        if triggered_codes:
            result = df["ts_code"].isin(triggered_codes)

        return result

    def _detect_t0(self, df: pd.DataFrame) -> pd.Series:
        """检测当日 T0 放量突破。"""
        pct_chg = df.get("pct_chg", pd.Series(dtype=float)).fillna(0)
        vol_ratio = df.get("vol_ratio", pd.Series(dtype=float)).fillna(0)
        vol = df.get("vol", pd.Series(dtype=float)).fillna(0)
        return (
            (pct_chg >= self.params["min_t0_pct_chg"])
            & (vol_ratio >= self.params["min_t0_vol_ratio"])
            & (vol > 0)
        )
