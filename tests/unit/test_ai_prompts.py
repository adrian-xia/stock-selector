"""AI Prompt 模板单元测试。"""

from datetime import date

from app.ai.prompts import build_analysis_prompt
from app.strategy.pipeline import StockPick


class TestBuildAnalysisPrompt:
    """build_analysis_prompt() 测试。"""

    def _make_pick(self, ts_code: str = "600519.SH", name: str = "贵州茅台") -> StockPick:
        return StockPick(
            ts_code=ts_code,
            name=name,
            close=1705.20,
            pct_chg=1.25,
            matched_strategies=["ma-cross", "low-pe-high-roe"],
            match_count=2,
        )

    def test_basic_prompt_structure(self) -> None:
        picks = [self._make_pick()]
        market_data = {
            "600519.SH": {
                "close": 1705.20,
                "pct_chg": 1.25,
                "ma5": 1700.0,
                "ma10": 1690.0,
                "ma20": 1680.0,
                "ma60": 1650.0,
                "macd_dif": 5.2,
                "macd_dea": 3.1,
                "macd_hist": 2.1,
                "rsi6": 55.0,
                "vol_ratio": 1.2,
                "pe_ttm": 35.0,
                "pb": 12.0,
                "roe": 30.0,
                "profit_yoy": 15.0,
            },
        }
        prompt = build_analysis_prompt(picks, market_data, date(2026, 2, 7))

        # 检查基本结构
        assert "600519.SH" in prompt
        assert "贵州茅台" in prompt
        assert "2026-02-07" in prompt
        assert "analysis" in prompt
        assert "STRONG_BUY" in prompt
        assert "score" in prompt

    def test_multiple_stocks(self) -> None:
        picks = [
            self._make_pick("600519.SH", "贵州茅台"),
            self._make_pick("000858.SZ", "五粮液"),
            self._make_pick("600036.SH", "招商银行"),
        ]
        market_data = {}
        prompt = build_analysis_prompt(picks, market_data, date(2026, 2, 7))

        assert "3" in prompt  # 3 只股票
        assert "600519.SH" in prompt
        assert "000858.SZ" in prompt
        assert "600036.SH" in prompt

    def test_missing_market_data(self) -> None:
        """缺少市场数据时应标注"数据缺失"。"""
        picks = [self._make_pick()]
        market_data = {}  # 无数据
        prompt = build_analysis_prompt(picks, market_data, date(2026, 2, 7))

        assert "数据缺失" in prompt
        assert "600519.SH" in prompt

    def test_empty_picks(self) -> None:
        prompt = build_analysis_prompt([], {}, date(2026, 2, 7))
        assert "0" in prompt

    def test_partial_market_data(self) -> None:
        """部分指标缺失时不应报错。"""
        picks = [self._make_pick()]
        market_data = {
            "600519.SH": {
                "close": 1705.20,
                "pct_chg": 1.25,
                # 只有行情，无技术指标和基本面
            },
        }
        prompt = build_analysis_prompt(picks, market_data, date(2026, 2, 7))
        assert "600519.SH" in prompt
