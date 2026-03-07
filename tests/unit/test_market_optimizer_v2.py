"""测试 V2 MarketOptimizer 分支。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.optimization.market_optimizer import MarketOptimizer


@pytest.mark.asyncio
@patch("app.optimization.market_optimizer.execute_pipeline_v2", new_callable=AsyncMock)
async def test_evaluate_params_for_v2_trigger(mock_execute_pipeline_v2: AsyncMock) -> None:
    """V2 trigger 应走 execute_pipeline_v2 并按新公式评分。"""
    optimizer = MarketOptimizer(session_factory=object(), max_concurrency=1)
    sample_date = date(2026, 3, 7)
    mock_execute_pipeline_v2.return_value = SimpleNamespace(
        picks=[
            SimpleNamespace(ts_code="000001.SZ"),
            SimpleNamespace(ts_code="000002.SZ"),
        ]
    )

    result = await optimizer._evaluate_params(
        strategy_name="volume-breakout-trigger-v2",
        params={"min_vol_ratio": 2.0},
        sample_dates=[sample_date],
        returns_cache={
            (sample_date, "000001.SZ"): 0.10,
            (sample_date, "000002.SZ"): -0.05,
        },
    )

    assert result.total_picks == 2
    assert result.hit_rate_5d == pytest.approx(0.5)
    assert result.profit_loss_ratio == pytest.approx(2.0)
    assert result.score == pytest.approx(0.8875)
