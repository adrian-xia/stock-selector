"""市场状态评分（Market Regime）。

基于指数、情绪、量能四维度计算市场风险评分，输出仓位上限建议。
算法来源：设计文档 §6.1。

子项权重（V1）：
  risk_score = 0.35*volatility + 0.25*trend + 0.20*breadth + 0.20*sentiment
"""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

logger = logging.getLogger(__name__)


@dataclass
class MarketRegimeResult:
    """市场状态评分结果。"""

    risk_score: float  # 0~100，高分=高风险
    market_regime: str  # bull / range / bear
    position_cap: float  # 仓位上限 0.0~1.0
    volatility_risk: float
    trend_risk: float
    breadth_risk: float
    sentiment_risk: float
    details: dict  # 子项详情（调试用）


# ---------------------------------------------------------------------------
# 子项分段映射
# ---------------------------------------------------------------------------

def _calc_trend_risk(close_vs_ma60: float, close_vs_ma20: float) -> float:
    """趋势风险（指数收盘与 MA60 偏离度）。"""
    if close_vs_ma60 <= -0.03:
        risk = 80.0
    elif close_vs_ma60 <= 0.0:
        risk = 60.0
    elif close_vs_ma60 <= 0.03:
        risk = 40.0
    else:
        risk = 20.0

    # 补充：MA20 加罚
    if close_vs_ma20 < 0:
        risk = min(risk + 10, 90.0)
    return risk


def _calc_breadth_risk(advance_decline_ratio: float) -> float:
    """广度风险（涨跌家数比）。"""
    if advance_decline_ratio < 0.8:
        return 80.0
    elif advance_decline_ratio < 1.0:
        return 60.0
    elif advance_decline_ratio < 1.2:
        return 40.0
    else:
        return 20.0


def _calc_sentiment_risk(
    limit_up_down_ratio: float,
    max_consecutive_board: int = 5,
    yesterday_premium: float = 0.0,
) -> float:
    """情绪风险（涨跌停结构）。"""
    if limit_up_down_ratio < 0.5:
        risk = 80.0
    elif limit_up_down_ratio < 1.0:
        risk = 60.0
    elif limit_up_down_ratio < 2.0:
        risk = 40.0
    else:
        risk = 20.0

    # 辅助修正
    if max_consecutive_board <= 2:
        risk = min(risk + 10, 100.0)
    if yesterday_premium < -0.03:
        risk = min(risk + 10, 100.0)
    return risk


def _calc_volatility_risk(index_atr_pct: float) -> float:
    """波动率风险（ATR(14)/close）。"""
    if index_atr_pct > 3.5:
        return 80.0
    elif index_atr_pct > 2.5:
        return 60.0
    elif index_atr_pct > 1.5:
        return 40.0
    else:
        return 20.0


def _determine_regime(risk_score: float) -> str:
    """根据风险分判断市场状态。"""
    if risk_score >= 70:
        return "bear"
    elif risk_score >= 40:
        return "range"
    else:
        return "bull"


def _determine_position_cap(risk_score: float) -> float:
    """根据风险分确定仓位上限。"""
    if risk_score >= 70:
        return 0.30
    elif risk_score >= 40:
        return 0.60
    else:
        return 0.90


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------

async def calc_market_regime(
    session_factory: async_sessionmaker[AsyncSession],
    trade_date: date,
) -> MarketRegimeResult:
    """计算市场状态评分。

    从数据库查询指数和情绪指标，按设计文档 §6.1 计算四维度风险分。

    Args:
        session_factory: 数据库会话工厂
        trade_date: 交易日

    Returns:
        MarketRegimeResult
    """
    td_str = trade_date.strftime("%Y%m%d")
    details: dict = {}

    async with session_factory() as session:
        # ---- 1. 指数数据（沪深300）----
        close_vs_ma60 = 0.0
        close_vs_ma20 = 0.0
        index_atr_pct = 2.0  # 默认中性

        try:
            row = await session.execute(
                text(
                    "SELECT close, ma5, ma20, ma60 "
                    "FROM technical_daily "
                    "WHERE ts_code = '000300.SH' AND trade_date = :td"
                ),
                {"td": trade_date},
            )
            idx = row.first()
            if idx and idx.close and idx.ma60:
                close_vs_ma60 = (float(idx.close) - float(idx.ma60)) / float(idx.ma60)
                if idx.ma20:
                    close_vs_ma20 = (float(idx.close) - float(idx.ma20)) / float(idx.ma20)
                details["close_vs_ma60"] = round(close_vs_ma60, 4)
                details["close_vs_ma20"] = round(close_vs_ma20, 4)
        except Exception:
            logger.warning("[市场评分] 指数数据查询失败", exc_info=True)

        # ---- 2. ATR 估算（用指数近 14 日涨跌幅标准差近似）----
        try:
            row = await session.execute(
                text(
                    "SELECT STDDEV(pct_chg) AS atr_est "
                    "FROM stock_daily "
                    "WHERE ts_code = '000300.SH' "
                    "AND trade_date <= :td "
                    "ORDER BY trade_date DESC LIMIT 14"
                ),
                {"td": trade_date},
            )
            atr_row = row.first()
            if atr_row and atr_row.atr_est:
                index_atr_pct = float(atr_row.atr_est)
                details["index_atr_pct"] = round(index_atr_pct, 4)
        except Exception:
            pass

        # ---- 3. 涨跌家数（advance/decline）----
        advance_decline_ratio = 1.0
        try:
            row = await session.execute(
                text(
                    "SELECT "
                    "  SUM(CASE WHEN pct_chg > 0 THEN 1 ELSE 0 END) AS advances, "
                    "  SUM(CASE WHEN pct_chg < 0 THEN 1 ELSE 0 END) AS declines "
                    "FROM stock_daily WHERE trade_date = :td"
                ),
                {"td": trade_date},
            )
            ad = row.first()
            if ad and ad.advances and ad.declines and ad.declines > 0:
                advance_decline_ratio = float(ad.advances) / float(ad.declines)
                details["advance_decline_ratio"] = round(advance_decline_ratio, 2)
        except Exception:
            pass

        # ---- 4. 涨跌停数据 ----
        limit_up_down_ratio = 1.0
        try:
            row = await session.execute(
                text(
                    "SELECT "
                    "  SUM(CASE WHEN pct_chg >= 9.8 THEN 1 ELSE 0 END) AS limit_up, "
                    "  SUM(CASE WHEN pct_chg <= -9.8 THEN 1 ELSE 0 END) AS limit_down "
                    "FROM stock_daily WHERE trade_date = :td"
                ),
                {"td": trade_date},
            )
            lt = row.first()
            if lt and lt.limit_up is not None and lt.limit_down is not None:
                lu = int(lt.limit_up)
                ld = max(int(lt.limit_down), 1)
                limit_up_down_ratio = lu / ld
                details["limit_up"] = lu
                details["limit_down"] = int(lt.limit_down)
        except Exception:
            pass

    # ---- 计算子项 ----
    volatility_risk = _calc_volatility_risk(index_atr_pct)
    trend_risk = _calc_trend_risk(close_vs_ma60, close_vs_ma20)
    breadth_risk = _calc_breadth_risk(advance_decline_ratio)
    sentiment_risk = _calc_sentiment_risk(limit_up_down_ratio)

    # ---- 加权总分 ----
    risk_score = (
        0.35 * volatility_risk
        + 0.25 * trend_risk
        + 0.20 * breadth_risk
        + 0.20 * sentiment_risk
    )

    market_regime = _determine_regime(risk_score)
    position_cap = _determine_position_cap(risk_score)

    logger.info(
        "[市场评分] %s: risk=%.1f regime=%s cap=%.2f "
        "(vol=%.0f trend=%.0f breadth=%.0f sent=%.0f)",
        trade_date, risk_score, market_regime, position_cap,
        volatility_risk, trend_risk, breadth_risk, sentiment_risk,
    )

    return MarketRegimeResult(
        risk_score=round(risk_score, 2),
        market_regime=market_regime,
        position_cap=position_cap,
        volatility_risk=volatility_risk,
        trend_risk=trend_risk,
        breadth_risk=breadth_risk,
        sentiment_risk=sentiment_risk,
        details=details,
    )
