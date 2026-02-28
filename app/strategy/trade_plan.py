"""交易计划生成器：基于 T 日选股结果生成 T+1 触发条件。"""

import logging
from datetime import date
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)

# 策略类型分组
_BREAKOUT_STRATEGIES = {
    "ma-long-arrange", "boll-breakthrough", "donchian-breakout", "volume-breakout",
}
_REVERSAL_STRATEGIES = {
    "rsi-oversold", "volume-contraction-pullback", "first-negative-reversal",
}
_VALUE_STRATEGIES = {
    "low-pe-high-roe", "high-dividend", "pb-value", "financial-safety",
}
_VOLUME_STRATEGIES = {
    "shrink-volume-rise", "volume-price-stable", "extreme-shrink-bottom",
    "volume-surge-continuation", "pullback-half-rule",
}
_STABILIZATION_STRATEGIES = {
    "volume-price-pattern",
}

RISK_REWARD_RATIO = 2.0


def _classify_strategy(strategy_name: str) -> str:
    """返回策略所属类型。"""
    if strategy_name in _BREAKOUT_STRATEGIES:
        return "breakout"
    if strategy_name in _REVERSAL_STRATEGIES:
        return "reversal"
    if strategy_name in _VALUE_STRATEGIES:
        return "value"
    if strategy_name in _VOLUME_STRATEGIES:
        return "volume_signal"
    if strategy_name in _STABILIZATION_STRATEGIES:
        return "stabilization"
    return "breakout"  # 默认归为突破型


def _build_plan(
    ts_code: str,
    plan_date: date,
    valid_date: date,
    strategy_name: str,
    indicators: dict[str, Any],
) -> dict:
    """根据策略类型和技术指标构建单条交易计划。"""
    close = float(indicators.get("close") or 0)
    ma5 = float(indicators.get("ma5") or close)
    ma20 = float(indicators.get("ma20") or close)
    boll_upper = float(indicators.get("boll_upper") or close)
    boll_mid = float(indicators.get("boll_mid") or close)
    donchian_upper = float(indicators.get("donchian_upper") or close)
    atr14 = float(indicators.get("atr14") or close * 0.02)
    recent_high = float(indicators.get("recent_high") or close)
    recent_low = float(indicators.get("recent_low") or close * 0.95)

    trigger_type = _classify_strategy(strategy_name)

    if trigger_type == "breakout":
        # 突破型：触发价取近期高点或布林上轨（取较大值）
        trigger_price = max(recent_high, boll_upper, donchian_upper)
        trigger_condition = f"突破 {trigger_price:.2f} 买入"
        stop_loss = max(ma20, boll_mid)

    elif trigger_type == "reversal":
        # 超跌反弹型：当前收盘价，次日开盘不低于 97% 即可
        trigger_price = close
        floor = close * 0.97
        trigger_condition = f"开盘价不低于 {floor:.2f} 买入"
        stop_loss = recent_low

    elif trigger_type == "value":
        # 价值型：小幅回调买入
        trigger_price = round(close * 0.98, 2)
        trigger_condition = f"回调至 {trigger_price:.2f} 附近买入"
        stop_loss = round(close * 0.95, 2)

    elif trigger_type == "stabilization":
        # 量价配合：缩量回踩企稳买入，止损用 T0 最低价
        trigger_price = close
        trigger_condition = "缩量回踩企稳，次日开盘买入"
        stop_loss = recent_low  # 会被观察池的 t0_low 覆盖（见下方增强）
        take_profit = round(close * 1.15, 2)  # 15% 止盈

    else:  # volume_signal
        # 量价型：当前收盘价，放量突破 MA5
        trigger_price = close
        trigger_condition = f"放量突破 {ma5:.2f} 买入" if ma5 > 0 else "缩量企稳后放量买入"
        stop_loss = ma20

    # 止盈：止损距离 * risk_reward_ratio
    if stop_loss and trigger_price and trigger_price > stop_loss:
        loss_dist = trigger_price - stop_loss
        take_profit = round(trigger_price + loss_dist * RISK_REWARD_RATIO, 2)
    else:
        take_profit = None

    return {
        "ts_code": ts_code,
        "plan_date": plan_date,
        "valid_date": valid_date,
        "direction": "buy",
        "trigger_type": trigger_type,
        "trigger_condition": trigger_condition,
        "trigger_price": round(trigger_price, 4) if trigger_price else None,
        "stop_loss": round(float(stop_loss), 4) if stop_loss else None,
        "take_profit": take_profit,
        "risk_reward_ratio": RISK_REWARD_RATIO,
        "source_strategy": strategy_name,
        "confidence": None,
        "triggered": None,
        "actual_price": None,
    }


class TradePlanGenerator:
    """基于选股结果和技术指标生成交易计划。"""

    async def get_next_trade_date(self, session, current_date: date) -> date:
        """查询 trade_calendar 获取下一个交易日。"""
        result = await session.execute(
            text("""
                SELECT cal_date FROM trade_calendar
                WHERE is_open = true AND cal_date > :d
                ORDER BY cal_date ASC
                LIMIT 1
            """),
            {"d": current_date},
        )
        row = result.fetchone()
        if row:
            return row[0]
        # 降级：返回下一个自然日
        from datetime import timedelta
        return current_date + timedelta(days=1)

    async def _get_indicators(
        self,
        session,
        ts_codes: list[str],
        target_date: date,
    ) -> dict[str, dict]:
        """获取近 20 日行情和技术指标，返回 ts_code -> indicators 字典。"""
        if not ts_codes:
            return {}

        placeholders = ", ".join(f":c{i}" for i in range(len(ts_codes)))
        code_params = {f"c{i}": code for i, code in enumerate(ts_codes)}

        # 当日技术指标
        result = await session.execute(
            text(f"""
                SELECT
                    sd.ts_code,
                    sd.close,
                    td.ma5, td.ma20,
                    td.boll_upper, td.boll_mid,
                    td.donchian_upper,
                    td.atr14
                FROM stock_daily sd
                LEFT JOIN technical_daily td
                    ON sd.ts_code = td.ts_code AND sd.trade_date = td.trade_date
                WHERE sd.trade_date = :target_date
                  AND sd.ts_code IN ({placeholders})
            """),
            {"target_date": target_date, **code_params},
        )
        rows = result.fetchall()
        indicators: dict[str, dict] = {}
        for row in rows:
            indicators[row[0]] = {
                "close": row[1],
                "ma5": row[2],
                "ma20": row[3],
                "boll_upper": row[4],
                "boll_mid": row[5],
                "donchian_upper": row[6],
                "atr14": row[7],
            }

        # 近 20 日高低点
        result2 = await session.execute(
            text(f"""
                SELECT ts_code, MAX(high) AS recent_high, MIN(low) AS recent_low
                FROM stock_daily
                WHERE trade_date <= :target_date
                  AND ts_code IN ({placeholders})
                  AND trade_date >= (
                      SELECT cal_date FROM trade_calendar
                      WHERE is_open = true AND cal_date <= :target_date
                      ORDER BY cal_date DESC
                      OFFSET 19 LIMIT 1
                  )
                GROUP BY ts_code
            """),
            {"target_date": target_date, **code_params},
        )
        for row in result2.fetchall():
            if row[0] in indicators:
                indicators[row[0]]["recent_high"] = row[1]
                indicators[row[0]]["recent_low"] = row[2]

        return indicators

    async def _get_watchpool_data(
        self, session, ts_codes: list[str], target_date: date
    ) -> dict[str, dict]:
        """从观察池获取已触发股票的 T0 数据。"""
        if not ts_codes:
            return {}
        placeholders = ", ".join(f":c{i}" for i in range(len(ts_codes)))
        code_params = {f"c{i}": code for i, code in enumerate(ts_codes)}
        result = await session.execute(
            text(f"""
                SELECT ts_code, t0_date, t0_low, t0_open, washout_days
                FROM strategy_watchpool
                WHERE status = 'triggered'
                  AND triggered_date = :target_date
                  AND ts_code IN ({placeholders})
            """),
            {"target_date": target_date, **code_params},
        )
        return {
            r.ts_code: {"t0_date": r.t0_date, "t0_low": r.t0_low,
                         "t0_open": r.t0_open, "washout_days": r.washout_days}
            for r in result.fetchall()
        }

    async def generate(
        self,
        session_factory,
        picks: list,
        target_date: date,
    ) -> list[dict]:
        """为选股结果生成交易计划并写入数据库。

        Args:
            session_factory: 异步数据库会话工厂
            picks: StockPick 列表
            target_date: T 日（选股日期）

        Returns:
            生成的交易计划列表（dict）
        """
        if not picks:
            return []

        async with session_factory() as session:
            # 获取 T+1 交易日
            valid_date = await self.get_next_trade_date(session, target_date)

            # 收集所有股票代码
            ts_codes = list({p.ts_code for p in picks})

            # 获取技术指标
            indicators_map = await self._get_indicators(session, ts_codes, target_date)

            # 获取观察池数据（用于量价配合策略的精确止损）
            watchpool_map = await self._get_watchpool_data(session, ts_codes, target_date)

            plans: list[dict] = []
            for pick in picks:
                indicators = indicators_map.get(pick.ts_code, {})
                if not indicators.get("close"):
                    logger.warning("[TradePlan] %s 无行情数据，跳过", pick.ts_code)
                    continue

                primary_strategy = pick.matched_strategies[0] if pick.matched_strategies else "unknown"
                plan = _build_plan(
                    ts_code=pick.ts_code,
                    plan_date=target_date,
                    valid_date=valid_date,
                    strategy_name=primary_strategy,
                    indicators=indicators,
                )

                # 量价配合策略：用观察池 T0 数据覆盖止损
                wp = watchpool_map.get(pick.ts_code)
                if wp and primary_strategy == "volume-price-pattern":
                    plan["stop_loss"] = round(float(wp["t0_low"]), 4)
                    plan["trigger_condition"] = (
                        f"缩量回踩企稳：T0日期{wp['t0_date']}，"
                        f"回踩{wp['washout_days']}天"
                    )

                plans.append(plan)

            if not plans:
                return []

            # 批量写入（增量，不覆盖历史）
            saved = 0
            for plan in plans:
                await session.execute(
                    text("""
                        INSERT INTO trade_plans (
                            ts_code, plan_date, valid_date,
                            direction, trigger_type, trigger_condition, trigger_price,
                            stop_loss, take_profit, risk_reward_ratio,
                            source_strategy, confidence,
                            triggered, actual_price
                        ) VALUES (
                            :ts_code, :plan_date, :valid_date,
                            :direction, :trigger_type, :trigger_condition, :trigger_price,
                            :stop_loss, :take_profit, :risk_reward_ratio,
                            :source_strategy, :confidence,
                            :triggered, :actual_price
                        )
                        ON CONFLICT DO NOTHING
                    """),
                    plan,
                )
                saved += 1

            await session.commit()
            logger.info(
                "[TradePlan] 生成完成：%d 条计划（日期：%s，有效日：%s）",
                saved, target_date, valid_date,
            )
            return plans
