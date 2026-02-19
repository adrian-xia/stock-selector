"""测试告警 REST API。"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.alert import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertHistoryResponse,
)


class TestAlertSchemas:
    """测试 Pydantic 模型。"""

    def test_alert_rule_create(self):
        body = AlertRuleCreate(
            ts_code="600519.SH",
            rule_type="price_break",
            params={"target_price": 1800, "direction": "above"},
            cooldown_minutes=60,
        )
        assert body.ts_code == "600519.SH"
        assert body.rule_type == "price_break"
        assert body.cooldown_minutes == 60

    def test_alert_rule_create_defaults(self):
        body = AlertRuleCreate(ts_code="600519.SH", rule_type="strategy_signal")
        assert body.params == {}
        assert body.cooldown_minutes == 30

    def test_alert_rule_update_partial(self):
        body = AlertRuleUpdate(enabled=False)
        assert body.enabled is False
        assert body.params is None
        assert body.cooldown_minutes is None

    def test_alert_rule_response(self):
        resp = AlertRuleResponse(
            id=1,
            ts_code="600519.SH",
            rule_type="price_break",
            params={"target_price": 1800},
            enabled=True,
            cooldown_minutes=30,
            last_triggered_at=None,
            created_at=datetime(2026, 2, 19, 10, 0, 0),
        )
        assert resp.id == 1
        assert resp.enabled is True

    def test_alert_history_response(self):
        resp = AlertHistoryResponse(
            id=1,
            rule_id=1,
            ts_code="600519.SH",
            rule_type="price_break",
            message="600519.SH 价格 1850.00 突破 1800.00",
            notified=True,
            triggered_at=datetime(2026, 2, 19, 10, 30, 0),
        )
        assert resp.notified is True
        assert "突破" in resp.message


class TestRealtimeAPI:
    """测试实时监控 API 模型。"""

    def test_status_response(self):
        from app.api.realtime import StatusResponse
        resp = StatusResponse(
            collecting=True,
            watchlist_count=5,
            watchlist=["600519.SH"],
            websocket_connections=2,
            max_stocks=50,
        )
        assert resp.collecting is True
        assert resp.max_stocks == 50
