"""V2 优化 API 测试。"""

from datetime import date

import pytest
from fastapi import HTTPException

from app.api.optimization import (
    OptimizationRunRequest,
    get_param_space,
    run_optimization,
)


class TestOptimizationApiV2:
    """仅保留 V2 trigger 的优化入口测试。"""

    @pytest.mark.asyncio
    async def test_get_param_space_for_v2_trigger(self) -> None:
        response = await get_param_space("volume-breakout-trigger-v2")

        assert response.strategy_name == "volume-breakout-trigger-v2"
        assert response.display_name == "放量突破"
        assert response.default_params
        assert response.param_space

    @pytest.mark.asyncio
    async def test_get_param_space_rejects_non_trigger(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await get_param_space("quality-score-v2")

        assert exc_info.value.status_code == 400
        assert "trigger" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_run_optimization_rejects_non_trigger(self) -> None:
        with pytest.raises(HTTPException) as exc_info:
            await run_optimization(
                OptimizationRunRequest(
                    strategy_name="quality-score-v2",
                    algorithm="grid",
                    stock_codes=["600519.SH"],
                    start_date=date(2025, 1, 1),
                    end_date=date(2025, 2, 1),
                )
            )

        assert exc_info.value.status_code == 400
        assert "trigger" in str(exc_info.value.detail)
