"""测试 Pipeline 各层逻辑（使用 mock 数据库会话）。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.strategy.pipeline import (
    PipelineResult,
    StockPick,
    _layer4_rank_and_topn,
    _layer5_ai_placeholder,
    execute_pipeline,
)


class TestStockPick:
    """测试 StockPick 数据类。"""

    def test_creation(self) -> None:
        pick = StockPick(
            ts_code="600519.SH",
            name="贵州茅台",
            close=1705.20,
            pct_chg=1.25,
            matched_strategies=["ma-cross"],
            match_count=1,
        )
        assert pick.ts_code == "600519.SH"
        assert pick.match_count == 1

    def test_defaults(self) -> None:
        pick = StockPick(ts_code="000001.SZ", name="平安银行", close=10.0, pct_chg=0.5)
        assert pick.matched_strategies == []
        assert pick.match_count == 0


class TestPipelineResult:
    """测试 PipelineResult 数据类。"""

    def test_creation(self) -> None:
        result = PipelineResult(target_date=date(2026, 2, 7))
        assert result.picks == []
        assert result.layer_stats == {}
        assert result.elapsed_ms == 0


class TestLayer4RankAndTopN:
    """测试 Layer 4 排序和 Top N 逻辑。"""

    def test_rank_by_match_count(self) -> None:
        """按命中策略数降序排序。"""
        df = pd.DataFrame({
            "ts_code": ["A", "B", "C"],
            "close": [10.0, 20.0, 30.0],
            "pct_chg": [1.0, 2.0, 3.0],
        })
        name_map = {"A": "股票A", "B": "股票B", "C": "股票C"}
        hit_records = {
            "A": ["s1"],
            "B": ["s1", "s2", "s3"],
            "C": ["s1", "s2"],
        }
        picks = _layer4_rank_and_topn(df, name_map, hit_records, top_n=10)
        assert len(picks) == 3
        assert picks[0].ts_code == "B"  # 3 个策略命中
        assert picks[1].ts_code == "C"  # 2 个策略命中
        assert picks[2].ts_code == "A"  # 1 个策略命中

    def test_top_n_cutoff(self) -> None:
        """Top N 截断。"""
        df = pd.DataFrame({
            "ts_code": [f"S{i}" for i in range(10)],
            "close": [10.0] * 10,
            "pct_chg": [1.0] * 10,
        })
        name_map = {f"S{i}": f"股票{i}" for i in range(10)}
        hit_records = {f"S{i}": ["s1"] for i in range(10)}
        picks = _layer4_rank_and_topn(df, name_map, hit_records, top_n=3)
        assert len(picks) == 3

    def test_empty_df(self) -> None:
        """空 DataFrame 返回空列表。"""
        df = pd.DataFrame()
        picks = _layer4_rank_and_topn(df, {}, {}, top_n=10)
        assert picks == []


class TestLayer5AIPlaceholder:
    """测试 Layer 5 AI 占位。"""

    @pytest.mark.asyncio
    async def test_passthrough(self) -> None:
        """直接透传输入。"""
        picks = [
            StockPick(ts_code="A", name="A", close=10.0, pct_chg=1.0),
            StockPick(ts_code="B", name="B", close=20.0, pct_chg=2.0),
        ]
        result = await _layer5_ai_placeholder(picks)
        assert result == picks
        assert len(result) == 2


class TestExecutePipelineEmptyStrategies:
    """测试空策略列表。"""

    @pytest.mark.asyncio
    async def test_empty_strategies_returns_empty(self) -> None:
        """空策略列表直接返回空结果。"""
        mock_factory = AsyncMock()
        result = await execute_pipeline(
            session_factory=mock_factory,
            strategy_names=[],
            target_date=date(2026, 2, 7),
        )
        assert isinstance(result, PipelineResult)
        assert result.picks == []
        assert result.elapsed_ms >= 0
