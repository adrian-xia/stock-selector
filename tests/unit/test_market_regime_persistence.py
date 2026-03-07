"""测试市场状态持久化链路。"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.strategy.market_regime import (
    MarketRegime,
    _normalize_regime,
    compute_and_store_regime,
    get_market_regime,
)


def _mock_session_factory(session: AsyncMock) -> MagicMock:
    factory = MagicMock()
    factory.return_value.__aenter__ = AsyncMock(return_value=session)
    factory.return_value.__aexit__ = AsyncMock(return_value=False)
    return factory


def test_normalize_regime_supports_bytes_and_invalid_values() -> None:
    """状态规范化应支持 bytes，并忽略非法值。"""
    assert _normalize_regime(b"bull") == MarketRegime.BULL
    assert _normalize_regime("range") == MarketRegime.RANGE
    assert _normalize_regime("unknown") is None


@pytest.mark.asyncio
async def test_get_market_regime_reads_from_db_when_redis_misses() -> None:
    """Redis miss 时应回退读取持久化表。"""
    target_date = date(2026, 3, 7)
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = SimpleNamespace(regime="bear")
    session.execute.return_value = result
    session_factory = _mock_session_factory(session)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with patch("app.strategy.market_regime.get_redis", return_value=mock_redis):
        regime = await get_market_regime(session_factory, target_date)

    assert regime == MarketRegime.BEAR
    session.execute.assert_awaited_once()
    mock_redis.get.assert_awaited_once()
    mock_redis.set.assert_awaited_once_with(
        "market:regime:2026-03-07",
        "bear",
        ex=7 * 24 * 60 * 60,
    )


@pytest.mark.asyncio
async def test_get_market_regime_falls_back_to_compute_when_db_misses() -> None:
    """Redis 和 DB 都 miss 时应回退实时计算。"""
    target_date = date(2026, 3, 7)
    session = AsyncMock()
    result = MagicMock()
    result.first.return_value = None
    session.execute.return_value = result
    session_factory = _mock_session_factory(session)

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None

    with (
        patch("app.strategy.market_regime.get_redis", return_value=mock_redis),
        patch(
            "app.strategy.market_regime.compute_and_store_regime",
            new=AsyncMock(return_value=MarketRegime.BULL),
        ) as mock_compute,
    ):
        regime = await get_market_regime(session_factory, target_date)

    assert regime == MarketRegime.BULL
    session.execute.assert_awaited_once()
    mock_compute.assert_awaited_once_with(session_factory, target_date)


@pytest.mark.asyncio
async def test_compute_and_store_regime_upserts_persistent_snapshot() -> None:
    """实时计算后应 UPSERT 到持久化表并写入 Redis。"""
    target_date = date(2026, 3, 7)
    session = AsyncMock()
    prev_date_result = MagicMock()
    prev_date_result.scalar.return_value = date(2026, 3, 6)

    current_result = MagicMock()
    current_result.first.return_value = SimpleNamespace(close=101, ma20=95, ma60=90)

    prev_ma20_result = MagicMock()
    prev_ma20_result.first.return_value = SimpleNamespace(ma20=94)

    upsert_result = MagicMock()
    session.execute.side_effect = [
        prev_date_result,
        current_result,
        prev_ma20_result,
        upsert_result,
    ]
    session_factory = _mock_session_factory(session)

    mock_redis = AsyncMock()
    with patch("app.strategy.market_regime.get_redis", return_value=mock_redis):
        regime = await compute_and_store_regime(session_factory, target_date)

    assert regime == MarketRegime.BULL
    session.commit.assert_awaited_once()
    assert session.execute.await_count == 4

    upsert_call = session.execute.await_args_list[-1]
    params = upsert_call.args[1]
    assert params["trade_date"] == target_date
    assert params["benchmark_code"] == "000001.SH"
    assert params["regime"] == "bull"
    assert params["close"] == 101.0
    assert params["ma20"] == 95.0
    assert params["ma60"] == 90.0
    assert params["prev_ma20"] == 94.0

    mock_redis.set.assert_awaited_once_with(
        "market:regime:2026-03-07",
        "bull",
        ex=7 * 24 * 60 * 60,
    )
