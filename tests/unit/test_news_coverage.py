"""新闻覆盖范围解析测试。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.news.coverage import resolve_news_coverage_universe


class TestNewsCoverage:
    @pytest.mark.asyncio
    @patch("app.api.realtime.get_watchlist_snapshot", return_value=["000001.SZ", "300750.SZ"])
    async def test_union_candidate_and_watchlist(self, _mock_watchlist):
        """覆盖范围应按多选并集返回。"""
        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_session.execute = AsyncMock(return_value=[])
        mock_factory = MagicMock(return_value=mock_session)

        result = await resolve_news_coverage_universe(
            target_date=date(2026, 3, 6),
            session_factory=mock_factory,
            scopes=["daily_candidates", "realtime_watchlist"],
            candidate_codes=["600519.SH", "000001.SZ"],
        )

        assert result.ts_codes == ["000001.SZ", "300750.SZ", "600519.SH"]
        assert result.code_sources["000001.SZ"] == ["daily_candidates", "realtime_watchlist"]
        assert result.code_sources["600519.SH"] == ["daily_candidates"]
        assert result.code_sources["300750.SZ"] == ["realtime_watchlist"]
