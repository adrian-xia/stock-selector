"""告警规则引擎：评估规则、防抖动冷却、触发通知。"""

import json
import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.alert import AlertHistory, AlertRule
from app.realtime.indicator import Signal

logger = logging.getLogger(__name__)

COOLDOWN_KEY_PREFIX = "alert:cooldown:"


class AlertEngine:
    """告警规则评估器。"""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession], redis_client=None, notification_manager=None):
        self._session_factory = session_factory
        self._redis = redis_client
        self._notification = notification_manager

    async def evaluate_price(self, ts_code: str, current_price: float) -> None:
        """评估价格预警规则。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AlertRule).where(
                    AlertRule.ts_code == ts_code,
                    AlertRule.rule_type == "price_break",
                    AlertRule.enabled.is_(True),
                )
            )
            rules = result.scalars().all()

            for rule in rules:
                params = rule.params or {}
                target = params.get("target_price", 0)
                direction = params.get("direction", "above")

                triggered = False
                if direction == "above" and current_price >= target:
                    triggered = True
                elif direction == "below" and current_price <= target:
                    triggered = True

                if triggered:
                    await self._trigger(session, rule, f"{ts_code} 价格 {current_price:.2f} {'突破' if direction == 'above' else '跌破'} {target:.2f}")

            await session.commit()

    async def evaluate_signal(self, signal: Signal) -> None:
        """评估策略信号预警规则。"""
        async with self._session_factory() as session:
            result = await session.execute(
                select(AlertRule).where(
                    AlertRule.ts_code == signal.ts_code,
                    AlertRule.rule_type == "strategy_signal",
                    AlertRule.enabled.is_(True),
                )
            )
            rules = result.scalars().all()

            for rule in rules:
                params = rule.params or {}
                signal_type = params.get("signal_type", "")
                if signal_type and signal_type != signal.signal_type:
                    continue
                await self._trigger(session, rule, signal.message)

            await session.commit()

    async def _trigger(self, session: AsyncSession, rule: AlertRule, message: str) -> None:
        """触发告警：检查冷却 → 写入历史 → 发送通知。"""
        # 检查冷却
        if await self._is_cooling(rule):
            return

        # 写入告警历史
        history = AlertHistory(
            rule_id=rule.id,
            ts_code=rule.ts_code,
            rule_type=rule.rule_type,
            message=message,
            notified=False,
        )
        session.add(history)

        # 更新规则最后触发时间
        rule.last_triggered_at = datetime.now()

        # 设置冷却
        await self._set_cooldown(rule)

        # 发送通知
        notified = False
        if self._notification:
            try:
                await self._notification.send(
                    level="WARNING",
                    title=f"告警: {rule.ts_code}",
                    message=message,
                )
                notified = True
            except Exception:
                logger.warning("[AlertEngine] 通知发送失败", exc_info=True)

        history.notified = notified
        logger.info("[AlertEngine] 告警触发: %s (notified=%s)", message, notified)

    async def _is_cooling(self, rule: AlertRule) -> bool:
        """检查规则是否在冷却期内。"""
        if not self._redis:
            return False
        key = f"{COOLDOWN_KEY_PREFIX}{rule.ts_code}:{rule.id}"
        try:
            val = await self._redis.get(key)
            return val is not None
        except Exception:
            return False

    async def _set_cooldown(self, rule: AlertRule) -> None:
        """设置冷却标记（Redis TTL 自动过期）。"""
        if not self._redis:
            return
        key = f"{COOLDOWN_KEY_PREFIX}{rule.ts_code}:{rule.id}"
        ttl = (rule.cooldown_minutes or 30) * 60
        try:
            await self._redis.setex(key, ttl, "1")
        except Exception:
            logger.warning("[AlertEngine] 设置冷却失败: %s", key, exc_info=True)

