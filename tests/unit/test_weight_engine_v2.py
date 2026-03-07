"""测试 V2 权重引擎。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.strategy.market_regime import MarketRegime
from app.strategy.weight_engine import (
    compute_rolling_performance,
    get_signal_group_coefficient,
    get_style_bonus,
)


def test_signal_group_coefficient_matrix() -> None:
    """信号组系数矩阵应符合设计预期。"""
    assert get_signal_group_coefficient(MarketRegime.BULL, "aggressive") == 1.2
    assert get_signal_group_coefficient(MarketRegime.RANGE, "trend") == 0.9
    assert get_signal_group_coefficient(MarketRegime.BEAR, "bottom") == 1.2


def test_style_bonus_uses_delta_from_one() -> None:
    """风格增益应使用相对 1.0 的微调值。"""
    bonus = get_style_bonus({"growth": 0.8, "dividend": 0.2}, MarketRegime.BULL)
    assert round(bonus, 4) == 0.12


@pytest.mark.asyncio
async def test_compute_rolling_performance_clamps_to_micro_adjustment() -> None:
    """滚动绩效应收敛到 [0.8, 1.2]。"""
    session = AsyncMock()
    result = MagicMock()
    result.fetchall.return_value = [
        ("volume-breakout-trigger-v2", 40, 28, 2.5, 1.0),
        ("atr-breakout-trigger-v2", 10, 5, 0.5, 0.2),
    ]
    session.execute.return_value = result

    perf = await compute_rolling_performance(
        session,
        ["volume-breakout-trigger-v2", "atr-breakout-trigger-v2"],
        date(2026, 3, 7),
    )

    assert 1.0 < perf["volume-breakout-trigger-v2"] <= 1.2
    assert perf["atr-breakout-trigger-v2"] == 1.0

