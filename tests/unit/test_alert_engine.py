"""测试告警规则引擎。"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import AlertRule
from app.realtime.alert_engine import AlertEngine
from app.realtime.indicator import Signal


def _make_engine(rules=None, redis_cooling=False):
    """创建测试用 AlertEngine。"""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    sf = MagicMock(return_value=session)

    # mock 查询结果
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = rules or []
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.commit = AsyncMock()

    redis = AsyncMock()
    redis.get = AsyncMock(return_value=b"1" if redis_cooling else None)
    redis.setex = AsyncMock()

    notification = AsyncMock()
    notification.send = AsyncMock()

    engine = AlertEngine(sf, redis, notification)
    return engine, session, redis, notification


def _make_rule(rule_type="price_break", params=None, enabled=True, cooldown=30):
    rule = MagicMock(spec=AlertRule)
    rule.id = 1
    rule.ts_code = "600519.SH"
    rule.rule_type = rule_type
    rule.params = params or {}
    rule.enabled = enabled
    rule.cooldown_minutes = cooldown
    rule.last_triggered_at = None
    return rule


class TestEvaluatePrice:
    """测试价格预警评估。"""

    @pytest.mark.asyncio
    async def test_price_above_trigger(self):
        rule = _make_rule(params={"target_price": 1800, "direction": "above"})
        engine, session, redis, notif = _make_engine([rule])
        await engine.evaluate_price("600519.SH", 1850.0)
        session.add.assert_called_once()
        notif.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_price_below_trigger(self):
        rule = _make_rule(params={"target_price": 1800, "direction": "below"})
        engine, session, redis, notif = _make_engine([rule])
        await engine.evaluate_price("600519.SH", 1750.0)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_price_not_triggered(self):
        rule = _make_rule(params={"target_price": 1800, "direction": "above"})
        engine, session, redis, notif = _make_engine([rule])
        await engine.evaluate_price("600519.SH", 1700.0)
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_cooldown_prevents_trigger(self):
        rule = _make_rule(params={"target_price": 1800, "direction": "above"})
        engine, session, redis, notif = _make_engine([rule], redis_cooling=True)
        await engine.evaluate_price("600519.SH", 1850.0)
        session.add.assert_not_called()
        notif.send.assert_not_called()


class TestEvaluateSignal:
    """测试策略信号评估。"""

    @pytest.mark.asyncio
    async def test_signal_trigger(self):
        rule = _make_rule(rule_type="strategy_signal", params={"signal_type": "ma_golden_cross"})
        engine, session, redis, notif = _make_engine([rule])
        signal = Signal(ts_code="600519.SH", signal_type="ma_golden_cross", message="MA5 上穿 MA10")
        await engine.evaluate_signal(signal)
        session.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_type_mismatch(self):
        rule = _make_rule(rule_type="strategy_signal", params={"signal_type": "rsi_oversold"})
        engine, session, redis, notif = _make_engine([rule])
        signal = Signal(ts_code="600519.SH", signal_type="ma_golden_cross", message="MA5 上穿 MA10")
        await engine.evaluate_signal(signal)
        session.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_signal_empty_type_matches_all(self):
        rule = _make_rule(rule_type="strategy_signal", params={"signal_type": ""})
        engine, session, redis, notif = _make_engine([rule])
        signal = Signal(ts_code="600519.SH", signal_type="ma_golden_cross", message="MA5 上穿 MA10")
        await engine.evaluate_signal(signal)
        session.add.assert_called_once()


class TestCooldown:
    """测试冷却机制。"""

    @pytest.mark.asyncio
    async def test_set_cooldown(self):
        rule = _make_rule(params={"target_price": 1800, "direction": "above"}, cooldown=60)
        engine, session, redis, notif = _make_engine([rule])
        await engine.evaluate_price("600519.SH", 1850.0)
        redis.setex.assert_called_once()
        # 验证 TTL = 60 * 60 = 3600
        call_args = redis.setex.call_args
        assert call_args[0][1] == 3600

    @pytest.mark.asyncio
    async def test_no_redis_no_cooldown(self):
        """无 Redis 时不检查冷却。"""
        rule = _make_rule(params={"target_price": 1800, "direction": "above"})
        session = AsyncMock()
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        sf = MagicMock(return_value=session)
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [rule]
        session.execute = AsyncMock(return_value=result_mock)
        session.add = MagicMock()
        session.commit = AsyncMock()

        engine = AlertEngine(sf, redis_client=None, notification_manager=None)
        await engine.evaluate_price("600519.SH", 1850.0)
        session.add.assert_called_once()
