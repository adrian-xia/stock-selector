"""测试策略引擎 API：run / list / schema 端点。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.strategy import (
    StrategyRunRequest,
    get_strategy_schema,
    list_strategies,
    run_strategy,
)
from app.strategy.factory import StrategyMeta
from app.strategy.pipeline import PipelineResult, StockPick


class TestRunStrategy:
    """测试 POST /strategy/run 端点。"""

    @patch("app.api.strategy.execute_pipeline", new_callable=AsyncMock)
    @patch("app.api.strategy.StrategyFactory")
    async def test_run_success(
        self, mock_factory: MagicMock, mock_pipeline: AsyncMock
    ) -> None:
        """正常执行应返回 StrategyRunResponse。"""
        # 模拟工厂返回可用策略（MagicMock 的 name 需要通过 spec 设置）
        meta_mock = MagicMock()
        meta_mock.name = "ma-cross"
        mock_factory.get_all.return_value = [meta_mock]

        # 模拟 pipeline 返回结果
        mock_pipeline.return_value = PipelineResult(
            target_date=date(2026, 2, 8),
            picks=[
                StockPick(
                    ts_code="600519.SH",
                    name="贵州茅台",
                    close=1700.0,
                    pct_chg=2.5,
                    matched_strategies=["ma-cross"],
                    match_count=1,
                ),
            ],
            layer_stats={"layer1": 100, "layer2": 10},
            elapsed_ms=500,
            ai_enabled=False,
        )

        req = StrategyRunRequest(
            strategy_names=["ma-cross"],
            target_date=date(2026, 2, 8),
            top_n=30,
        )
        response = await run_strategy(req)

        assert response.target_date == date(2026, 2, 8)
        assert response.total_picks == 1
        assert response.elapsed_ms == 500
        assert response.picks[0].ts_code == "600519.SH"
        assert response.picks[0].match_count == 1

    @patch("app.api.strategy.StrategyFactory")
    async def test_run_invalid_strategy_returns_400(
        self, mock_factory: MagicMock
    ) -> None:
        """传入不存在的策略名称应返回 400。"""
        meta_mock = MagicMock()
        meta_mock.name = "ma-cross"
        mock_factory.get_all.return_value = [meta_mock]

        req = StrategyRunRequest(
            strategy_names=["nonexistent-strategy"],
            top_n=30,
        )
        with pytest.raises(HTTPException) as exc_info:
            await run_strategy(req)

        assert exc_info.value.status_code == 400
        assert "nonexistent-strategy" in str(exc_info.value.detail)


class TestListStrategies:
    """测试 GET /strategy/list 端点。"""

    @patch("app.api.strategy.StrategyFactory")
    async def test_list_all_strategies(self, mock_factory: MagicMock) -> None:
        """不传 category 应返回全部策略。"""
        mock_factory.get_all.return_value = [
            StrategyMeta(
                name="ma-cross",
                display_name="均线金叉",
                category="technical",
                description="短期均线上穿长期均线",
                strategy_cls=MagicMock,
                default_params={"fast": 5, "slow": 10},
            ),
            StrategyMeta(
                name="low-pe-high-roe",
                display_name="低估值高成长",
                category="fundamental",
                description="市盈率低于30",
                strategy_cls=MagicMock,
                default_params={"pe_max": 30},
            ),
        ]

        response = await list_strategies(category=None)

        assert len(response.strategies) == 2
        assert response.strategies[0].name == "ma-cross"
        assert response.strategies[1].category == "fundamental"

    @patch("app.api.strategy.StrategyFactory")
    async def test_list_by_category(self, mock_factory: MagicMock) -> None:
        """传入 category 应只返回对应分类。"""
        mock_factory.get_by_category.return_value = [
            StrategyMeta(
                name="ma-cross",
                display_name="均线金叉",
                category="technical",
                description="短期均线上穿长期均线",
                strategy_cls=MagicMock,
                default_params={},
            ),
        ]

        response = await list_strategies(category="technical")

        assert len(response.strategies) == 1
        assert response.strategies[0].category == "technical"
        mock_factory.get_by_category.assert_called_once_with("technical")


class TestGetStrategySchema:
    """测试 GET /strategy/schema/{name} 端点。"""

    @patch("app.api.strategy.StrategyFactory")
    async def test_get_existing_schema(self, mock_factory: MagicMock) -> None:
        """查询已注册策略应返回 schema。"""
        mock_factory.get_meta.return_value = StrategyMeta(
            name="ma-cross",
            display_name="均线金叉",
            category="technical",
            description="短期均线上穿长期均线",
            strategy_cls=MagicMock,
            default_params={"fast": 5, "slow": 10},
        )

        response = await get_strategy_schema("ma-cross")

        assert response.name == "ma-cross"
        assert response.display_name == "均线金叉"
        assert response.default_params == {"fast": 5, "slow": 10}

    @patch("app.api.strategy.StrategyFactory")
    async def test_get_nonexistent_schema_returns_404(
        self, mock_factory: MagicMock
    ) -> None:
        """查询不存在的策略应返回 404。"""
        mock_factory.get_meta.side_effect = KeyError("策略 'xxx' 未注册")

        with pytest.raises(HTTPException) as exc_info:
            await get_strategy_schema("xxx")

        assert exc_info.value.status_code == 404
