"""V2 策略权重引擎。"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.strategy.base import SignalGroup
from app.strategy.market_regime import MarketRegime

logger = logging.getLogger(__name__)

REGIME_SIGNAL_COEFFICIENTS: dict[MarketRegime, dict[str, float]] = {
    MarketRegime.BULL: {
        SignalGroup.AGGRESSIVE.value: 1.2,
        SignalGroup.TREND.value: 1.0,
        SignalGroup.BOTTOM.value: 0.7,
    },
    MarketRegime.RANGE: {
        SignalGroup.AGGRESSIVE.value: 0.8,
        SignalGroup.TREND.value: 0.9,
        SignalGroup.BOTTOM.value: 1.0,
    },
    MarketRegime.BEAR: {
        SignalGroup.AGGRESSIVE.value: 0.5,
        SignalGroup.TREND.value: 0.6,
        SignalGroup.BOTTOM.value: 1.2,
    },
}

REGIME_STYLE_COEFFICIENTS: dict[MarketRegime, dict[str, float]] = {
    MarketRegime.BULL: {
        "dividend": 0.8,
        "growth": 1.2,
    },
    MarketRegime.RANGE: {
        "dividend": 1.1,
        "growth": 0.9,
    },
    MarketRegime.BEAR: {
        "dividend": 1.3,
        "growth": 0.7,
    },
}


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, value))


def get_signal_group_coefficient(
    regime: MarketRegime,
    signal_group: str | SignalGroup,
) -> float:
    """获取某信号组在市场状态下的系数。"""
    group_value = signal_group.value if isinstance(signal_group, SignalGroup) else signal_group
    return REGIME_SIGNAL_COEFFICIENTS.get(regime, {}).get(group_value, 1.0)


def get_style_bonus(
    tags: dict[str, float],
    regime: MarketRegime,
) -> float:
    """计算风格增益。

    设计矩阵给出的是风格偏好系数；这里将其转换为相对 1.0 的增益/减益，
    保持该项只做微调，不喧宾夺主。
    """
    if not tags:
        return 0.0

    total_bonus = 0.0
    coeffs = REGIME_STYLE_COEFFICIENTS.get(regime, {})
    for style_key, strength in tags.items():
        coeff = coeffs.get(style_key)
        if coeff is None:
            continue
        total_bonus += float(strength) * (coeff - 1.0)

    return _clamp(total_bonus, -0.3, 0.3)


async def compute_rolling_performance(
    session: AsyncSession,
    strategy_names: list[str],
    target_date: date,
    *,
    lookback_days: int = 30,
    period: str = "5d",
    min_samples: int = 20,
) -> dict[str, float]:
    """计算策略滚动绩效乘数。

    结果收敛到 [0.8, 1.2]，只做轻量微调。
    """
    if not strategy_names:
        return {}

    start_date = target_date - timedelta(days=lookback_days)
    perf_map = {name: 1.0 for name in strategy_names}

    try:
        result = await session.execute(
            text(
                """
                SELECT
                    strategy_name,
                    COALESCE(SUM(total_picks), 0) AS total_picks,
                    COALESCE(SUM(win_count), 0) AS win_count,
                    COALESCE(
                        SUM(COALESCE(avg_return, 0) * total_picks)
                        / NULLIF(SUM(total_picks), 0),
                        0
                    ) AS weighted_avg_return,
                    COALESCE(STDDEV_POP(avg_return), 0) AS return_std
                FROM strategy_hit_stats
                WHERE strategy_name = ANY(:strategy_names)
                  AND period = :period
                  AND stat_date > :start_date
                  AND stat_date <= :target_date
                GROUP BY strategy_name
                """
            ),
            {
                "strategy_names": strategy_names,
                "period": period,
                "start_date": start_date,
                "target_date": target_date,
            },
        )

        for row in result.fetchall():
            strategy_name, total_picks, win_count, avg_return, return_std = row
            total_picks = int(total_picks or 0)
            if total_picks < min_samples:
                perf_map[strategy_name] = 1.0
                continue

            hit_rate = (float(win_count or 0) / total_picks) * 100 if total_picks else 50.0
            avg_return = float(avg_return or 0.0)
            return_std = float(return_std or 0.0)
            sharpe_proxy = avg_return / return_std if return_std > 0 else 0.0

            hit_component = _clamp((hit_rate - 50.0) / 50.0, -1.0, 1.0) * 0.08
            return_component = _clamp(avg_return / 10.0, -1.0, 1.0) * 0.07
            sharpe_component = _clamp(sharpe_proxy / 2.0, -1.0, 1.0) * 0.05

            perf_map[strategy_name] = _clamp(
                1.0 + hit_component + return_component + sharpe_component,
                0.8,
                1.2,
            )
    except Exception:
        logger.warning("[WeightEngine] 读取滚动绩效失败，回退默认值", exc_info=True)

    return perf_map
