"""测试 V2 策略 API。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.strategy import (
    StrategyRunV2Request,
    list_strategies_v2,
    run_strategy_v2,
)
from app.strategy.base import SignalGroup, StrategyRole
from app.strategy.factory import StrategyMetaV2
from app.strategy.pipeline_v2 import PipelineV2Result, StockPickV2


class TestListStrategiesV2:
    """测试 GET /strategy/list-v2。"""

    @patch("app.api.strategy.StrategyFactoryV2")
    async def test_list_v2_triggers(self, mock_factory: MagicMock) -> None:
        meta = StrategyMetaV2(
            name="volume-breakout-trigger-v2",
            display_name="放量突破",
            role=StrategyRole.TRIGGER,
            signal_group=SignalGroup.AGGRESSIVE,
            description="价格创新高且成交量显著放大",
            strategy_cls=MagicMock,
            ai_rating=7.42,
            default_params={"min_vol_ratio": 2.0},
        )
        mock_factory.get_by_role.return_value = [meta]

        response = await list_strategies_v2()
        assert len(response.strategies) == 1
        assert response.strategies[0].category == "aggressive"


class TestRunStrategyV2:
    """测试 POST /strategy/run-v2。"""

    @patch("app.api.strategy.execute_pipeline_v2", new_callable=AsyncMock)
    @patch("app.api.strategy.StrategyFactoryV2")
    async def test_run_v2_success(
        self,
        mock_factory: MagicMock,
        mock_execute: AsyncMock,
    ) -> None:
        meta = MagicMock()
        meta.name = "volume-breakout-trigger-v2"
        mock_factory.get_by_role.return_value = [meta]

        mock_execute.return_value = PipelineV2Result(
            target_date=date(2026, 3, 7),
            picks=[
                StockPickV2(
                    ts_code="600519.SH",
                    name="贵州茅台",
                    close=1700.0,
                    pct_chg=2.5,
                    quality_score=88.0,
                    tags={"growth": 0.8},
                    triggered_signals=[{
                        "strategy": "volume-breakout-trigger-v2",
                        "group": "aggressive",
                        "confidence": 1.0,
                        "weight": 0.89,
                    }],
                    confirmed_bonus=0.2,
                    dynamic_weight=1.05,
                    style_bonus=0.16,
                    market_regime="bull",
                    final_score=1.123,
                ),
            ],
            layer_stats={"layer0": 100, "layer1": 30, "layer2_signals": 10, "layer3": 1},
            elapsed_ms=123,
            market_regime="bull",
        )

        response = await run_strategy_v2(
            StrategyRunV2Request(
                strategy_names=["volume-breakout-trigger-v2"],
                target_date=date(2026, 3, 7),
            )
        )

        assert response.total_picks == 1
        assert response.market_regime == "bull"
        assert response.picks[0].final_score == pytest.approx(1.123)

