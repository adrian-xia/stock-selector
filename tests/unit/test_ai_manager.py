"""AIManager 单元测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.clients.gemini import GeminiTimeoutError
from app.ai.manager import AIManager
from app.strategy.pipeline import StockPick


def _make_settings(api_key: str = "test-key", use_adc: bool = False) -> MagicMock:
    """构造 mock Settings。"""
    s = MagicMock()
    s.gemini_api_key = api_key
    s.gemini_use_adc = use_adc
    s.gemini_model_id = "gemini-2.0-flash"
    s.gemini_max_tokens = 4000
    s.gemini_timeout = 30
    s.gemini_max_retries = 2
    return s


def _make_picks(count: int = 3) -> list[StockPick]:
    """构造测试用 StockPick 列表。"""
    stocks = [
        ("600519.SH", "贵州茅台", 1705.20, 1.25),
        ("000858.SZ", "五粮液", 180.50, 0.80),
        ("600036.SH", "招商银行", 38.20, -0.50),
    ]
    return [
        StockPick(
            ts_code=code, name=name, close=close, pct_chg=pct,
            matched_strategies=["ma-cross"], match_count=1,
        )
        for code, name, close, pct in stocks[:count]
    ]


class TestAIManagerInit:
    """初始化测试。"""

    def test_enabled_with_api_key(self) -> None:
        manager = AIManager(_make_settings("valid-key"))
        assert manager.is_enabled is True

    def test_disabled_without_api_key(self) -> None:
        manager = AIManager(_make_settings(""))
        assert manager.is_enabled is False


class TestAIManagerAnalyze:
    """analyze() 方法测试。"""

    async def test_disabled_returns_original(self) -> None:
        """AI 未启用时直接返回原始 picks。"""
        manager = AIManager(_make_settings(""))
        picks = _make_picks()
        result = await manager.analyze(picks, {}, date(2026, 2, 7))
        assert result is picks
        assert all(p.ai_score is None for p in result)

    async def test_empty_picks_returns_empty(self) -> None:
        manager = AIManager(_make_settings())
        result = await manager.analyze([], {}, date(2026, 2, 7))
        assert result == []

    @patch("app.ai.manager.GeminiClient")
    async def test_successful_analysis(self, mock_client_cls: MagicMock) -> None:
        """成功分析后应设置 ai_score 并按分数排序。"""
        mock_client = MagicMock()
        mock_client.chat_json = AsyncMock(return_value={
            "analysis": [
                {"ts_code": "600519.SH", "score": 90, "signal": "STRONG_BUY", "reasoning": "强势"},
                {"ts_code": "000858.SZ", "score": 70, "signal": "BUY", "reasoning": "看好"},
                {"ts_code": "600036.SH", "score": 50, "signal": "HOLD", "reasoning": "中性"},
            ]
        })
        mock_client_cls.return_value = mock_client

        manager = AIManager(_make_settings())
        picks = _make_picks(3)
        result = await manager.analyze(picks, {}, date(2026, 2, 7))

        # 应按 ai_score 降序排列
        assert result[0].ai_score == 90
        assert result[0].ts_code == "600519.SH"
        assert result[1].ai_score == 70
        assert result[2].ai_score == 50

        # 应设置 ai_signal 和 ai_summary
        assert result[0].ai_signal == "STRONG_BUY"
        assert result[0].ai_summary == "强势"

    @patch("app.ai.manager.GeminiClient")
    async def test_timeout_graceful_degradation(self, mock_client_cls: MagicMock) -> None:
        """Gemini 超时时应返回原始 picks。"""
        mock_client = MagicMock()
        mock_client.chat_json = AsyncMock(
            side_effect=GeminiTimeoutError("timeout")
        )
        mock_client_cls.return_value = mock_client

        manager = AIManager(_make_settings())
        picks = _make_picks()
        result = await manager.analyze(picks, {}, date(2026, 2, 7))

        assert len(result) == 3
        assert all(p.ai_score is None for p in result)

    @patch("app.ai.manager.GeminiClient")
    async def test_invalid_response_graceful_degradation(self, mock_client_cls: MagicMock) -> None:
        """响应校验失败时应返回原始 picks。"""
        mock_client = MagicMock()
        mock_client.chat_json = AsyncMock(return_value={"wrong_field": []})
        mock_client_cls.return_value = mock_client

        manager = AIManager(_make_settings())
        picks = _make_picks()
        result = await manager.analyze(picks, {}, date(2026, 2, 7))

        assert len(result) == 3
        assert all(p.ai_score is None for p in result)

    @patch("app.ai.manager.GeminiClient")
    async def test_partial_response(self, mock_client_cls: MagicMock) -> None:
        """AI 只返回部分结果时，未匹配的股票 ai_score 为 None。"""
        mock_client = MagicMock()
        mock_client.chat_json = AsyncMock(return_value={
            "analysis": [
                {"ts_code": "600519.SH", "score": 90, "signal": "STRONG_BUY", "reasoning": "强势"},
                # 缺少 000858.SZ 和 600036.SH
            ]
        })
        mock_client_cls.return_value = mock_client

        manager = AIManager(_make_settings())
        picks = _make_picks(3)
        result = await manager.analyze(picks, {}, date(2026, 2, 7))

        # 有评分的排前面
        scored = [p for p in result if p.ai_score is not None]
        unscored = [p for p in result if p.ai_score is None]
        assert len(scored) == 1
        assert len(unscored) == 2
        assert scored[0].ts_code == "600519.SH"
