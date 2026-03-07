"""测试 V2 Pipeline Layer 3 融合公式。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.strategy.market_regime import MarketRegime
from app.strategy.pipeline_v2 import (
    Layer1Result,
    Layer2Signal,
    _layer3_fusion_ranking,
)


def _build_df() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "name": "平安银行",
                "close": 10.0,
                "pct_chg": 1.2,
            }
        ]
    )


def _build_layer1_result(
    *,
    quality_score: float = 0.0,
    tags: dict[str, float] | None = None,
) -> list[Layer1Result]:
    return [
        Layer1Result(
            ts_code="000001.SZ",
            passed_guard=True,
            quality_score=quality_score,
            tags=tags or {},
        )
    ]


def _build_signal(
    *,
    strategy_name: str = "volume-breakout-trigger-v2",
    signal_group: str = "aggressive",
    confidence: float = 1.0,
    static_weight: float = 1.0,
) -> list[Layer2Signal]:
    return [
        Layer2Signal(
            ts_code="000001.SZ",
            strategy_name=strategy_name,
            signal_group=signal_group,
            confidence=confidence,
            static_weight=static_weight,
        )
    ]


class _FixedConfirmer:
    def __init__(self, bonus: float, applicable_groups: list[str] | None = None) -> None:
        self.bonus = bonus
        self.applicable_groups = applicable_groups or []

    async def execute(self, df: pd.DataFrame, target_date: date) -> pd.Series:
        return pd.Series(self.bonus, index=df["ts_code"])


async def _run_layer3(
    *,
    market_regime: MarketRegime,
    layer1_results: list[Layer1Result],
    layer2_signals: list[Layer2Signal],
    rolling_performance: dict[str, float] | None = None,
    confirmers: list[object] | None = None,
) -> list:
    meta_list = [
        SimpleNamespace(
            name=f"confirmer-{idx}",
            strategy_cls=(lambda confirmer=confirmer: confirmer),
        )
        for idx, confirmer in enumerate(confirmers or [])
    ]

    with patch("app.strategy.pipeline_v2.StrategyFactoryV2.get_by_role", return_value=meta_list):
        return await _layer3_fusion_ranking(
            session=AsyncMock(),
            df=_build_df(),
            layer1_results=layer1_results,
            layer2_signals=layer2_signals,
            target_date=date(2026, 3, 7),
            market_regime=market_regime,
            rolling_performance=rolling_performance or {},
        )


@pytest.mark.asyncio
async def test_layer3_applies_regime_signal_coefficient_matrix() -> None:
    """同一 trigger 在不同市场状态下应应用不同系数。"""
    layer1_results = _build_layer1_result()
    signals = _build_signal()

    bull_pick = (
        await _run_layer3(
            market_regime=MarketRegime.BULL,
            layer1_results=layer1_results,
            layer2_signals=signals,
        )
    )[0]
    range_pick = (
        await _run_layer3(
            market_regime=MarketRegime.RANGE,
            layer1_results=layer1_results,
            layer2_signals=signals,
        )
    )[0]
    bear_pick = (
        await _run_layer3(
            market_regime=MarketRegime.BEAR,
            layer1_results=layer1_results,
            layer2_signals=signals,
        )
    )[0]

    assert bull_pick.final_score == pytest.approx(0.6)
    assert range_pick.final_score == pytest.approx(0.4)
    assert bear_pick.final_score == pytest.approx(0.25)


@pytest.mark.asyncio
async def test_layer3_caps_confirmer_bonus_at_point_six() -> None:
    """多个 confirmer 叠加后应封顶 0.6。"""
    picks = await _run_layer3(
        market_regime=MarketRegime.BULL,
        layer1_results=_build_layer1_result(),
        layer2_signals=_build_signal(),
        confirmers=[
            _FixedConfirmer(0.3, ["aggressive"]),
            _FixedConfirmer(0.3, ["aggressive"]),
            _FixedConfirmer(0.3, ["aggressive"]),
        ],
    )

    pick = picks[0]
    assert pick.confirmed_bonus == pytest.approx(0.6)
    assert pick.final_score == pytest.approx(0.9)


@pytest.mark.asyncio
async def test_layer3_uses_rolling_performance_and_falls_back_to_one() -> None:
    """rolling_performance 缺失时回退 1.0，有值时乘入 trigger 权重。"""
    layer1_results = _build_layer1_result()
    signals = _build_signal(strategy_name="volume-breakout-trigger-v2")

    fallback_pick = (
        await _run_layer3(
            market_regime=MarketRegime.BULL,
            layer1_results=layer1_results,
            layer2_signals=signals,
            rolling_performance={},
        )
    )[0]
    weighted_pick = (
        await _run_layer3(
            market_regime=MarketRegime.BULL,
            layer1_results=layer1_results,
            layer2_signals=signals,
            rolling_performance={"volume-breakout-trigger-v2": 1.2},
        )
    )[0]

    assert fallback_pick.dynamic_weight == pytest.approx(1.0)
    assert fallback_pick.final_score == pytest.approx(0.6)
    assert weighted_pick.dynamic_weight == pytest.approx(1.2)
    assert weighted_pick.final_score == pytest.approx(0.72)


@pytest.mark.asyncio
async def test_layer3_injects_style_bonus_into_final_score() -> None:
    """style_bonus 应由 tagger 强度注入最终得分。"""
    no_tag_pick = (
        await _run_layer3(
            market_regime=MarketRegime.BEAR,
            layer1_results=_build_layer1_result(),
            layer2_signals=_build_signal(signal_group="bottom"),
        )
    )[0]
    tagged_pick = (
        await _run_layer3(
            market_regime=MarketRegime.BEAR,
            layer1_results=_build_layer1_result(tags={"dividend": 1.0}),
            layer2_signals=_build_signal(signal_group="bottom"),
        )
    )[0]

    assert no_tag_pick.style_bonus == pytest.approx(0.0)
    assert tagged_pick.style_bonus == pytest.approx(0.3)
    assert tagged_pick.final_score - no_tag_pick.final_score == pytest.approx(0.03)


@pytest.mark.asyncio
async def test_layer3_filters_confirmers_by_mixed_signal_groups() -> None:
    """多 trigger 混合时，只叠加命中信号组的 confirmer。"""
    picks = await _run_layer3(
        market_regime=MarketRegime.BULL,
        layer1_results=_build_layer1_result(
            quality_score=50.0,
            tags={"growth": 0.5},
        ),
        layer2_signals=[
            Layer2Signal(
                ts_code="000001.SZ",
                strategy_name="volume-breakout-trigger-v2",
                signal_group="aggressive",
                confidence=1.0,
                static_weight=1.0,
            ),
            Layer2Signal(
                ts_code="000001.SZ",
                strategy_name="atr-breakout-trigger-v2",
                signal_group="trend",
                confidence=0.9,
                static_weight=0.8,
            ),
        ],
        rolling_performance={
            "volume-breakout-trigger-v2": 1.1,
            "atr-breakout-trigger-v2": 0.9,
        },
        confirmers=[
            _FixedConfirmer(0.2, ["aggressive"]),
            _FixedConfirmer(0.3, ["trend"]),
            _FixedConfirmer(0.4, ["bottom"]),
            _FixedConfirmer(0.1, []),
        ],
    )

    assert len(picks) == 1
    pick = picks[0]

    assert len(pick.triggered_signals) == 2
    assert pick.dynamic_weight == pytest.approx(1.0)
    assert pick.confirmed_bonus == pytest.approx(0.6)
    assert pick.style_bonus == pytest.approx(0.1)
    assert pick.final_score == pytest.approx(1.494)


@pytest.mark.asyncio
async def test_layer3_caps_confirmer_bonus_with_three_mixed_triggers() -> None:
    """同一股票命中 3 个 trigger 时，confirmer 总和超过 0.6 仍应封顶。"""
    picks = await _run_layer3(
        market_regime=MarketRegime.BULL,
        layer1_results=_build_layer1_result(),
        layer2_signals=[
            Layer2Signal(
                ts_code="000001.SZ",
                strategy_name="volume-breakout-trigger-v2",
                signal_group="aggressive",
                confidence=1.0,
                static_weight=1.0,
            ),
            Layer2Signal(
                ts_code="000001.SZ",
                strategy_name="atr-breakout-trigger-v2",
                signal_group="trend",
                confidence=1.0,
                static_weight=1.0,
            ),
            Layer2Signal(
                ts_code="000001.SZ",
                strategy_name="extreme-shrink-bottom-trigger-v2",
                signal_group="bottom",
                confidence=1.0,
                static_weight=1.0,
            ),
        ],
        rolling_performance={
            "volume-breakout-trigger-v2": 1.0,
            "atr-breakout-trigger-v2": 1.0,
            "extreme-shrink-bottom-trigger-v2": 1.0,
        },
        confirmers=[
            _FixedConfirmer(0.3, ["aggressive"]),
            _FixedConfirmer(0.3, ["trend"]),
            _FixedConfirmer(0.3, ["bottom"]),
            _FixedConfirmer(0.2, []),
        ],
    )

    assert len(picks) == 1
    pick = picks[0]

    assert len(pick.triggered_signals) == 3
    assert pick.dynamic_weight == pytest.approx(1.0)
    assert pick.confirmed_bonus == pytest.approx(0.6)
    assert pick.style_bonus == pytest.approx(0.0)
    assert pick.final_score == pytest.approx(1.75)
