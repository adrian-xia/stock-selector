"""测试 V4 日常执行器。"""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from app.strategy.v4_daily_runner import execute_volume_price_pattern_daily


def _build_session_factory() -> MagicMock:
    """构造通用 AsyncSession 工厂 mock。"""
    session = AsyncMock()
    session.__aenter__.return_value = session
    session.__aexit__.return_value = False
    return MagicMock(return_value=session)


@pytest.mark.asyncio
@patch("app.strategy.v4_daily_runner.save_strategy_picks", new_callable=AsyncMock)
@patch("app.strategy.v4_daily_runner._fetch_daily_snapshot", new_callable=AsyncMock)
@patch("app.strategy.v4_daily_runner._load_strategy_config", new_callable=AsyncMock)
async def test_execute_volume_price_pattern_daily_skip_when_disabled(
    mock_load_config: AsyncMock,
    mock_fetch_snapshot: AsyncMock,
    mock_save_picks: AsyncMock,
) -> None:
    """策略禁用时应直接跳过。"""
    mock_load_config.return_value = (False, {})

    picks = await execute_volume_price_pattern_daily(
        target_date=date(2026, 3, 7),
        session_factory=_build_session_factory(),
        save_picks=True,
    )

    assert picks == []
    mock_fetch_snapshot.assert_not_awaited()
    mock_save_picks.assert_not_awaited()


@pytest.mark.asyncio
@patch("app.strategy.v4_daily_runner.save_strategy_picks", new_callable=AsyncMock)
@patch("app.strategy.v4_daily_runner._load_triggered_meta", new_callable=AsyncMock)
@patch("app.strategy.v4_daily_runner._fetch_daily_snapshot", new_callable=AsyncMock)
@patch("app.strategy.v4_daily_runner._load_strategy_config", new_callable=AsyncMock)
@patch("app.strategy.v4_daily_runner.VolumePricePatternStrategy")
async def test_execute_volume_price_pattern_daily_builds_and_saves_picks(
    mock_strategy_cls: MagicMock,
    mock_load_config: AsyncMock,
    mock_fetch_snapshot: AsyncMock,
    mock_load_meta: AsyncMock,
    mock_save_picks: AsyncMock,
) -> None:
    """命中结果应转换为通用 StockPick 并落库。"""
    mock_load_config.return_value = (True, {"min_vol_ratio": 1.5})
    mock_fetch_snapshot.return_value = pd.DataFrame(
        [
            {
                "ts_code": "000001.SZ",
                "name": "平安银行",
                "open": 12.1,
                "high": 12.6,
                "low": 11.9,
                "close": 12.5,
                "vol": 1234567,
                "pct_chg": 3.2,
                "vol_ratio": 1.8,
            },
            {
                "ts_code": "000002.SZ",
                "name": "万科A",
                "open": 8.8,
                "high": 9.0,
                "low": 8.7,
                "close": 8.9,
                "vol": 765432,
                "pct_chg": 1.1,
                "vol_ratio": 1.2,
            },
        ]
    )
    mock_load_meta.return_value = {
        "000001.SZ": {
            "washout_days": 2,
            "sector_score": 1.0,
        }
    }

    strategy_instance = MagicMock()
    strategy_instance.filter_batch = AsyncMock(
        return_value=pd.Series([True, False], dtype=bool)
    )
    mock_strategy_cls.return_value = strategy_instance

    picks = await execute_volume_price_pattern_daily(
        target_date=date(2026, 3, 7),
        session_factory=_build_session_factory(),
        save_picks=True,
    )

    assert len(picks) == 1
    assert picks[0].ts_code == "000001.SZ"
    assert picks[0].matched_strategies == ["volume-price-pattern"]
    assert picks[0].weighted_score == pytest.approx(87.0)
    mock_save_picks.assert_awaited_once()

