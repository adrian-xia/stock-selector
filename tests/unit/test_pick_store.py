"""测试 strategy_picks 写入逻辑。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.strategy.pick_store import save_strategy_picks
from app.strategy.pick_types import StockPick


@pytest.mark.asyncio
async def test_save_strategy_picks_fallback_to_weighted_score():
    """ai_score 为空时应回退到 weighted_score。"""
    pick = StockPick(
        ts_code="600519.SH",
        name="贵州茅台",
        close=1700.0,
        pct_chg=2.5,
        matched_strategies=["volume-breakout-trigger-v2"],
        match_count=1,
        weighted_score=88.6,
    )

    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    session_factory = MagicMock(return_value=session)

    count = await save_strategy_picks(
        session_factory=session_factory,
        strategy_names=["volume-breakout-trigger-v2"],
        target_date=date(2026, 3, 7),
        picks=[pick],
    )

    assert count == 1
    params = session.execute.await_args_list[0].args[1]
    assert params["pick_score"] == pytest.approx(88.6)
