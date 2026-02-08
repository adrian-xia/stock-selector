"""AI 数据模型单元测试。"""

import pytest
from pydantic import ValidationError

from app.ai.schemas import AIAnalysisItem, AIAnalysisResponse


class TestAIAnalysisItem:
    """AIAnalysisItem 校验测试。"""

    def test_valid_item(self) -> None:
        item = AIAnalysisItem(
            ts_code="600519.SH",
            score=85,
            signal="BUY",
            reasoning="均线多头排列",
        )
        assert item.ts_code == "600519.SH"
        assert item.score == 85
        assert item.signal == "BUY"

    def test_score_min_boundary(self) -> None:
        item = AIAnalysisItem(
            ts_code="600519.SH", score=0, signal="STRONG_SELL", reasoning="test"
        )
        assert item.score == 0

    def test_score_max_boundary(self) -> None:
        item = AIAnalysisItem(
            ts_code="600519.SH", score=100, signal="STRONG_BUY", reasoning="test"
        )
        assert item.score == 100

    def test_score_below_min_raises(self) -> None:
        with pytest.raises(ValidationError):
            AIAnalysisItem(
                ts_code="600519.SH", score=-1, signal="SELL", reasoning="test"
            )

    def test_score_above_max_raises(self) -> None:
        with pytest.raises(ValidationError):
            AIAnalysisItem(
                ts_code="600519.SH", score=150, signal="BUY", reasoning="test"
            )

    def test_invalid_signal_raises(self) -> None:
        with pytest.raises(ValidationError):
            AIAnalysisItem(
                ts_code="600519.SH", score=50, signal="INVALID", reasoning="test"
            )

    def test_all_valid_signals(self) -> None:
        for signal in ["STRONG_BUY", "BUY", "HOLD", "SELL", "STRONG_SELL"]:
            item = AIAnalysisItem(
                ts_code="test", score=50, signal=signal, reasoning="test"
            )
            assert item.signal == signal


class TestAIAnalysisResponse:
    """AIAnalysisResponse 校验测试。"""

    def test_valid_response(self) -> None:
        resp = AIAnalysisResponse.model_validate({
            "analysis": [
                {
                    "ts_code": "600519.SH",
                    "score": 85,
                    "signal": "BUY",
                    "reasoning": "看好",
                },
            ]
        })
        assert len(resp.analysis) == 1
        assert resp.analysis[0].ts_code == "600519.SH"

    def test_empty_analysis(self) -> None:
        resp = AIAnalysisResponse.model_validate({"analysis": []})
        assert len(resp.analysis) == 0

    def test_missing_analysis_field_raises(self) -> None:
        with pytest.raises(ValidationError):
            AIAnalysisResponse.model_validate({"results": []})

    def test_invalid_item_in_analysis_raises(self) -> None:
        with pytest.raises(ValidationError):
            AIAnalysisResponse.model_validate({
                "analysis": [{"ts_code": "test", "score": 200, "signal": "BUY", "reasoning": "x"}]
            })
