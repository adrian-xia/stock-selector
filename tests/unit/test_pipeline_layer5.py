"""Pipeline Layer 5 AI 集成测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd

from app.strategy.pipeline import StockPick, _layer5_ai_analysis


class TestLayer5AIAnalysis:
    """Layer 5 AI 终审测试。"""

    def _make_picks(self) -> list[StockPick]:
        return [
            StockPick(
                ts_code="600519.SH", name="贵州茅台",
                close=1705.20, pct_chg=1.25,
                matched_strategies=["ma-cross"], match_count=1,
            ),
            StockPick(
                ts_code="000858.SZ", name="五粮液",
                close=180.50, pct_chg=0.80,
                matched_strategies=["rsi-oversold"], match_count=1,
            ),
        ]

    def _make_snapshot(self) -> pd.DataFrame:
        return pd.DataFrame({
            "ts_code": ["600519.SH", "000858.SZ"],
            "close": [1705.20, 180.50],
            "pct_chg": [1.25, 0.80],
            "ma5": [1700.0, 178.0],
            "rsi6": [55.0, 28.0],
        })

    @patch("app.ai.manager.get_ai_manager")
    async def test_ai_disabled_passthrough(self, mock_get_manager: MagicMock) -> None:
        """AI 未启用时直接透传。"""
        mock_manager = MagicMock()
        mock_manager.is_enabled = False
        mock_get_manager.return_value = mock_manager

        picks = self._make_picks()
        result = await _layer5_ai_analysis(picks, self._make_snapshot(), date(2026, 2, 7))

        assert len(result) == 2
        assert result[0].ts_code == "600519.SH"
        mock_manager.analyze.assert_not_called()

    @patch("app.ai.manager.get_ai_manager")
    async def test_ai_enabled_calls_analyze(self, mock_get_manager: MagicMock) -> None:
        """AI 启用时应调用 analyze。"""
        mock_manager = MagicMock()
        mock_manager.is_enabled = True

        scored_picks = self._make_picks()
        scored_picks[0].ai_score = 90
        scored_picks[1].ai_score = 70
        mock_manager.analyze = AsyncMock(return_value=scored_picks)
        mock_get_manager.return_value = mock_manager

        picks = self._make_picks()
        result = await _layer5_ai_analysis(picks, self._make_snapshot(), date(2026, 2, 7))

        mock_manager.analyze.assert_called_once()
        assert result[0].ai_score == 90

    @patch("app.ai.manager.get_ai_manager")
    async def test_empty_snapshot(self, mock_get_manager: MagicMock) -> None:
        """空 snapshot 时仍应调用 analyze（market_data 为空 dict）。"""
        mock_manager = MagicMock()
        mock_manager.is_enabled = True
        mock_manager.analyze = AsyncMock(return_value=self._make_picks())
        mock_get_manager.return_value = mock_manager

        picks = self._make_picks()
        await _layer5_ai_analysis(picks, pd.DataFrame(), date(2026, 2, 7))

        call_args = mock_manager.analyze.call_args
        assert call_args[0][1] == {}  # market_data 应为空 dict
