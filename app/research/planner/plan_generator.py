"""交易计划生成器：将融合排名转化为增强交易计划。

基于个股融合排名、市场状态、行业评分，生成带风控规则的交易计划。
"""

import logging
from dataclasses import dataclass
from datetime import date

from app.research.scoring.market_regime import MarketRegimeResult
from app.research.scoring.stock_rank_fusion import RankedStock

logger = logging.getLogger(__name__)

# 计划类型推断阈值
_PLAN_TYPE_THRESHOLDS = {
    "breakout": 0.7,   # 策略分 > 70 分视为突破型
    "pullback": 0.5,   # 中等分视为回调型
    "reversal": 0.0,   # 低分视为反转型
}


@dataclass
class TradePlanInput:
    """交易计划生成输入。"""

    ranked_stock: RankedStock
    market_regime: MarketRegimeResult
    sector_score: float
    sector_name: str


def generate_trade_plans(
    ranked_stocks: list[RankedStock],
    market_regime: MarketRegimeResult,
    sector_scores: dict[str, float],
    trade_date: date,
    valid_date: date,
    max_plans: int = 20,
) -> list[dict]:
    """生成增强交易计划列表。

    Args:
        ranked_stocks: 融合排名后的个股列表
        market_regime: 市场状态评分
        sector_scores: {sector_code: final_score}
        trade_date: 交易日
        valid_date: 下一个有效交易日
        max_plans: 最大计划数

    Returns:
        可直接写入 trade_plan_daily_ext 的字典列表
    """
    plans: list[dict] = []

    for stock in ranked_stocks[:max_plans]:
        # 推断计划类型
        plan_type = _infer_plan_type(stock.strategy_score_n)

        # 仓位建议：受市场风险约束
        base_position = 0.10  # 单票基础仓位 10%
        confidence_factor = stock.stock_rank / 100.0
        position = base_position * (1 - market_regime.risk_score / 100) * confidence_factor
        position = round(max(0.02, min(position, market_regime.position_cap / 3)), 2)

        # 风控规则
        entry_rule, stop_loss_rule, take_profit_rule = _generate_rules(
            plan_type, market_regime
        )
        trigger_price, stop_loss_price, take_profit_price, risk_reward_ratio = (
            _generate_execution_prices(plan_type, stock.close, market_regime)
        )

        # 极端风险兜底（设计文档 §6.4）
        emergency_exit_config = {
            "trigger": {"type": "gap_down_breach", "threshold": 0.02},
            "action": {"type": "exit_at_open", "max_slippage_bps": 50},
            "priority": 1,
        }

        # 风险标记
        risk_flags: list[str] = []
        if market_regime.risk_score >= 70:
            risk_flags.append("HIGH_MARKET_RISK")
        if stock.strategy_score_n < 30:
            risk_flags.append("LOW_STRATEGY_SCORE")

        # 推理依据
        reasoning = [
            f"策略分: {stock.strategy_score_n:.0f}",
            f"行业分: {stock.sector_score_n:.0f}",
            f"资金分: {stock.moneyflow_score_n:.0f}",
            f"融合排名: {stock.stock_rank:.1f}",
            f"市场风险: {market_regime.risk_score:.0f} ({market_regime.market_regime})",
        ]
        if stock.source_strategies:
            reasoning.append(f"来源策略: {', '.join(stock.source_strategies)}")

        sector_code = ""
        for code, score in sector_scores.items():
            if abs(score - stock.sector_score_n) < 0.01:
                sector_code = code
                break

        plans.append({
            "trade_date": trade_date,
            "valid_date": valid_date,
            "ts_code": stock.ts_code,
            "source_strategy": stock.source_strategies[0] if stock.source_strategies else "unknown",
            "plan_type": plan_type,
            "plan_status": "PENDING",
            "direction": "buy",
            "trigger_price": trigger_price,
            "stop_loss_price": stop_loss_price,
            "take_profit_price": take_profit_price,
            "risk_reward_ratio": risk_reward_ratio,
            "triggered": None,
            "actual_price": None,
            "entry_rule": entry_rule,
            "stop_loss_rule": stop_loss_rule,
            "take_profit_rule": take_profit_rule,
            "emergency_exit_text": "跳空低开超过2%时，开盘竞价或首分钟风控离场",
            "emergency_exit_config": emergency_exit_config,
            "position_suggestion": position,
            "market_regime": market_regime.market_regime,
            "market_risk_score": market_regime.risk_score,
            "sector_name": stock.sector_name,
            "sector_score": stock.sector_score_n,
            "confidence": stock.stock_rank,
            "reasoning": reasoning,
            "risk_flags": risk_flags,
        })

    logger.info("[计划生成] %s: 生成 %d 个交易计划", trade_date, len(plans))
    return plans


def _infer_plan_type(strategy_score: float) -> str:
    """根据策略分推断计划类型。"""
    if strategy_score >= 70:
        return "breakout"
    elif strategy_score >= 40:
        return "pullback"
    else:
        return "reversal"


def _generate_rules(
    plan_type: str, regime: MarketRegimeResult
) -> tuple[str, str, str]:
    """根据计划类型和市场状态生成交易规则。"""
    if plan_type == "breakout":
        entry = "突破前高后回踩确认不破，放量站稳"
        stop = f"跌破突破位 3%（弱市加严至 2%）" if regime.risk_score >= 60 else "跌破突破位 5%"
        profit = "盈利 8% 减半仓，15% 清仓" if regime.market_regime == "bull" else "盈利 5% 减半仓，10% 清仓"
    elif plan_type == "pullback":
        entry = "回踩均线支撑反弹，缩量企稳"
        stop = "跌破支撑位 2%" if regime.risk_score >= 60 else "跌破支撑位 3%"
        profit = "盈利 5% 减半仓，10% 清仓"
    else:  # reversal
        entry = "底部放量反弹，突破下降趋势线"
        stop = "跌破前低 2%"
        profit = "盈利 5% 减半仓，8% 清仓"

    return entry, stop, profit


def _generate_execution_prices(
    plan_type: str,
    close: float,
    regime: MarketRegimeResult,
) -> tuple[float | None, float | None, float | None, float]:
    """生成执行型数值计划字段。"""
    if close <= 0:
        return None, None, None, 2.0

    risk_reward_ratio = 2.0
    if plan_type == "breakout":
        trigger_price = round(close * 1.01, 4)
        stop_pct = 0.02 if regime.risk_score >= 60 else 0.05
        stop_loss_price = round(trigger_price * (1 - stop_pct), 4)
    elif plan_type == "pullback":
        trigger_price = round(close, 4)
        stop_pct = 0.02 if regime.risk_score >= 60 else 0.03
        stop_loss_price = round(close * (1 - stop_pct), 4)
    else:
        trigger_price = round(close * 1.005, 4)
        stop_loss_price = round(close * 0.98, 4)

    if trigger_price <= stop_loss_price:
        take_profit_price = round(trigger_price * 1.08, 4)
    else:
        take_profit_price = round(
            trigger_price + (trigger_price - stop_loss_price) * risk_reward_ratio,
            4,
        )

    return trigger_price, stop_loss_price, take_profit_price, risk_reward_ratio
