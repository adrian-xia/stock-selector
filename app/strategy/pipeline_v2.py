"""V2 Pipeline 执行引擎。

Layer 0: SQL 硬性排除
Layer 1: 质量底池（Guard + Scorer + Tagger）
Layer 2: 信号触发（Trigger）
Layer 3: 多因子融合排序（Confirmer + 市场状态感知）
"""

import logging
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.strategy.base import SignalGroup, StrategyRole, StrategySignal
from app.strategy.factory import StrategyFactoryV2

logger = logging.getLogger(__name__)


@dataclass
class Layer1Result:
    """Layer 1 输出结构。"""

    ts_code: str
    passed_guard: bool
    quality_score: float
    tags: dict[str, float]


@dataclass
class Layer2Signal:
    """Layer 2 信号结构。"""

    ts_code: str
    strategy_name: str
    signal_group: str
    confidence: float
    static_weight: float


@dataclass
class StockPickV2:
    """V2 选股结果。"""

    ts_code: str
    name: str
    close: float
    pct_chg: float
    quality_score: float
    tags: dict[str, float]
    triggered_signals: list[dict]
    confirmed_bonus: float
    final_score: float


async def execute_pipeline_v2(
    session: AsyncSession,
    target_date: date,
    top_n: int = 50,
) -> list[StockPickV2]:
    """执行 V2 Pipeline。

    Args:
        session: 数据库会话
        target_date: 目标日期
        top_n: 返回前 N 只股票

    Returns:
        list[StockPickV2]，按 final_score 降序排列
    """
    logger.info(f"[Pipeline V2] 开始执行，日期={target_date}, top_n={top_n}")

    # Layer 0: SQL 硬性排除
    df = await _layer0_sql_filter(session, target_date)
    if df.empty:
        logger.warning("[Pipeline V2] Layer 0 无股票通过")
        return []

    logger.info(f"[Pipeline V2] Layer 0 通过: {len(df)} 只")

    # Layer 1: 质量底池
    layer1_results = await _layer1_quality_pool(df, target_date)
    passed_stocks = [r for r in layer1_results if r.passed_guard]
    if not passed_stocks:
        logger.warning("[Pipeline V2] Layer 1 无股票通过 Guard")
        return []

    logger.info(f"[Pipeline V2] Layer 1 通过: {len(passed_stocks)} 只")

    # 构建 Layer 1 通过的股票 DataFrame
    passed_codes = [r.ts_code for r in passed_stocks]
    df_passed = df[df["ts_code"].isin(passed_codes)].copy()

    # Layer 2: 信号触发
    layer2_signals = await _layer2_trigger_signals(df_passed, target_date)
    if not layer2_signals:
        logger.warning("[Pipeline V2] Layer 2 无信号触发")
        return []

    logger.info(f"[Pipeline V2] Layer 2 触发信号: {len(layer2_signals)} 个")

    # Layer 3: 多因子融合排序
    picks = await _layer3_fusion_ranking(
        session, df_passed, layer1_results, layer2_signals, target_date
    )

    # 排序并返回 top_n
    picks.sort(key=lambda x: x.final_score, reverse=True)
    result = picks[:top_n]

    logger.info(f"[Pipeline V2] 完成，返回 {len(result)} 只股票")
    return result


async def _layer0_sql_filter(
    session: AsyncSession,
    target_date: date,
) -> pd.DataFrame:
    """Layer 0: SQL 硬性排除。"""
    min_list_date = target_date.replace(year=target_date.year - 1)  # 上市满1年简化

    query = text("""
        SELECT
            s.ts_code,
            s.name,
            sd.trade_date,
            sd.open,
            sd.high,
            sd.low,
            sd.close,
            sd.vol,
            sd.amount,
            sd.pct_chg,
            td.ma5, td.ma10, td.ma20, td.ma60,
            td.ma5_prev, td.ma20_prev, td.ma60_prev,
            td.macd_dif, td.macd_dea, td.macd_hist,
            td.macd_dif_prev,
            td.rsi6, td.rsi12,
            td.boll_upper, td.boll_mid, td.boll_lower,
            td.vol_ma5, td.vol_ma10, td.vol_ratio,
            td.atr14, td.atr14_prev,
            td.high_20, td.high_60,
            td.close_prev, td.open_prev, td.pct_chg_prev,
            db.turnover_rate,
            fi.roe, fi.eps, fi.pe_ttm, fi.pb, fi.dividend_yield,
            fi.debt_ratio, fi.current_ratio,
            fi.ocf_per_share, fi.profit_yoy
        FROM stocks s
        INNER JOIN stock_daily sd ON s.ts_code = sd.ts_code
        INNER JOIN technical_daily td ON sd.ts_code = td.ts_code AND sd.trade_date = td.trade_date
        LEFT JOIN daily_basic db ON sd.ts_code = db.ts_code AND sd.trade_date = db.trade_date
        LEFT JOIN finance_indicator fi ON s.ts_code = fi.ts_code
        WHERE sd.trade_date = :target_date
          AND s.status = 'L'
          AND s.name NOT LIKE '%ST%'
          AND s.name NOT LIKE '%退%'
          AND sd.amount >= 5000000
          AND sd.pct_chg > -9.9
          AND sd.pct_chg < 9.9
          AND s.list_date <= :min_list_date
          AND sd.vol > 0
    """)

    result = await session.execute(
        query, {"target_date": target_date, "min_list_date": min_list_date}
    )
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=result.keys())
    return df


async def _layer1_quality_pool(
    df: pd.DataFrame,
    target_date: date,
) -> list[Layer1Result]:
    """Layer 1: 质量底池（Guard + Scorer + Tagger）。"""
    results = []

    # 获取所有 Guard 策略
    guards = StrategyFactoryV2.get_by_role(StrategyRole.GUARD)
    guard_masks = []
    for meta in guards:
        strategy = meta.strategy_cls()
        mask = await strategy.execute(df, target_date)
        guard_masks.append(mask)

    # AND 逻辑：所有 Guard 都通过
    if guard_masks:
        passed_guard = pd.Series(True, index=df.index)
        for mask in guard_masks:
            passed_guard &= mask
    else:
        passed_guard = pd.Series(True, index=df.index)

    # 获取 Scorer 策略（当前只有 1 个）
    scorers = StrategyFactoryV2.get_by_role(StrategyRole.SCORER)
    if scorers:
        scorer_meta = scorers[0]
        scorer = scorer_meta.strategy_cls()
        quality_scores = await scorer.execute(df, target_date)
    else:
        quality_scores = pd.Series(50.0, index=df.index)

    # 获取 Tagger 策略
    taggers = StrategyFactoryV2.get_by_role(StrategyRole.TAGGER)
    all_tags = {}
    for meta in taggers:
        tagger = meta.strategy_cls()
        tag_dict = await tagger.execute(df, target_date)
        for style_key, strength_series in tag_dict.items():
            if style_key not in all_tags:
                all_tags[style_key] = strength_series
            else:
                # 多个 tagger 产出同一风格，取最大值
                all_tags[style_key] = pd.concat(
                    [all_tags[style_key], strength_series], axis=1
                ).max(axis=1)

    # 构建结果
    for idx, row in df.iterrows():
        ts_code = row["ts_code"]
        tags = {k: float(v.loc[idx]) for k, v in all_tags.items() if v.loc[idx] > 0}

        results.append(
            Layer1Result(
                ts_code=ts_code,
                passed_guard=bool(passed_guard.loc[idx]),
                quality_score=float(quality_scores.loc[idx]),
                tags=tags,
            )
        )

    return results


async def _layer2_trigger_signals(
    df: pd.DataFrame,
    target_date: date,
) -> list[Layer2Signal]:
    """Layer 2: 信号触发（Trigger）。"""
    signals = []

    triggers = StrategyFactoryV2.get_by_role(StrategyRole.TRIGGER)
    for meta in triggers:
        trigger = meta.strategy_cls()
        strategy_signals = await trigger.execute(df, target_date)

        for sig in strategy_signals:
            signals.append(
                Layer2Signal(
                    ts_code=sig.ts_code,
                    strategy_name=meta.name,
                    signal_group=meta.signal_group.value if meta.signal_group else "unknown",
                    confidence=sig.confidence,
                    static_weight=meta.ai_rating / 8.32,
                )
            )

    return signals


async def _layer3_fusion_ranking(
    session: AsyncSession,
    df: pd.DataFrame,
    layer1_results: list[Layer1Result],
    layer2_signals: list[Layer2Signal],
    target_date: date,
) -> list[StockPickV2]:
    """Layer 3: 多因子融合排序。"""
    # 构建 Layer 1 结果字典
    layer1_dict = {r.ts_code: r for r in layer1_results}

    # 按股票分组信号
    signals_by_stock = {}
    for sig in layer2_signals:
        if sig.ts_code not in signals_by_stock:
            signals_by_stock[sig.ts_code] = []
        signals_by_stock[sig.ts_code].append(sig)

    # 获取所有 Confirmer 策略
    confirmers = StrategyFactoryV2.get_by_role(StrategyRole.CONFIRMER)
    confirmer_bonuses = {}
    for meta in confirmers:
        confirmer = meta.strategy_cls()
        bonus_series = await confirmer.execute(df, target_date)
        confirmer_bonuses[meta.name] = bonus_series

    # 计算每只股票的最终得分
    picks = []
    for ts_code, signals in signals_by_stock.items():
        layer1_result = layer1_dict.get(ts_code)
        if not layer1_result or not layer1_result.passed_guard:
            continue

        # 获取股票基本信息
        stock_row = df[df["ts_code"] == ts_code].iloc[0]

        # 信号强度分：Σ(静态权重 × 置信度)
        signal_strength = sum(sig.static_weight * sig.confidence for sig in signals)

        # Confirmer 加分：叠加所有 confirmer，封顶 0.6
        total_bonus = 0.0
        for bonus_series in confirmer_bonuses.values():
            if ts_code in bonus_series.index:
                total_bonus += float(bonus_series.loc[ts_code])
        confirmed_bonus = min(total_bonus, 0.6)

        signal_strength += confirmed_bonus

        # 质量底分
        quality_score_normalized = layer1_result.quality_score / 100.0

        # 最终得分（简化版，暂不考虑动态加权和风格增益）
        final_score = signal_strength * 0.5 + quality_score_normalized * 0.5

        # 构建触发信号列表
        triggered_signals = [
            {
                "strategy": sig.strategy_name,
                "group": sig.signal_group,
                "confidence": sig.confidence,
                "weight": sig.static_weight,
            }
            for sig in signals
        ]

        picks.append(
            StockPickV2(
                ts_code=ts_code,
                name=stock_row["name"],
                close=float(stock_row["close"]),
                pct_chg=float(stock_row["pct_chg"]),
                quality_score=layer1_result.quality_score,
                tags=layer1_result.tags,
                triggered_signals=triggered_signals,
                confirmed_bonus=confirmed_bonus,
                final_score=final_score,
            )
        )

    return picks
