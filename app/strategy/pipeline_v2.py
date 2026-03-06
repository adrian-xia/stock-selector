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

    # 补充财务数据（Layer 1 的 Guard/Scorer/Tagger 需要）
    df = await _enrich_finance_data_v2(session, df, target_date)

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
    """Layer 0: SQL 硬性排除。

    复用 V1 pipeline 的 snapshot builder 思路：
    1. 先查当日行情 + 技术指标
    2. 再查前日技术指标（_prev 后缀）
    3. 不在 SQL 中 JOIN 财务数据（Layer 1 需要时再补充）
    """
    min_list_date = target_date.replace(year=target_date.year - 1)  # 上市满1年简化

    # 获取前一个交易日
    prev_date_sql = text("""
        SELECT MAX(trade_date)
        FROM stock_daily
        WHERE trade_date < :target_date
          AND vol > 0
        LIMIT 1
    """)
    prev_result = await session.execute(prev_date_sql, {"target_date": target_date})
    prev_date = prev_result.scalar()

    # 当日行情 + 技术指标
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
            td.macd_dif, td.macd_dea, td.macd_hist,
            td.rsi6, td.rsi12,
            td.boll_upper, td.boll_mid, td.boll_lower,
            td.vol_ma5, td.vol_ma10, td.vol_ratio,
            td.atr14,
            td.high_20, td.high_60,
            rtdb.turnover_rate
        FROM stocks s
        INNER JOIN stock_daily sd ON s.ts_code = sd.ts_code
        LEFT JOIN technical_daily td ON sd.ts_code = td.ts_code AND sd.trade_date = td.trade_date
        LEFT JOIN raw_tushare_daily_basic rtdb
            ON sd.ts_code = rtdb.ts_code
            AND rtdb.trade_date = :target_date_str
        WHERE sd.trade_date = :target_date
          AND s.list_status = 'L'
          AND s.name NOT LIKE '%ST%'
          AND s.name NOT LIKE '%退%'
          AND sd.amount >= 5000000
          AND sd.pct_chg > -9.9
          AND sd.pct_chg < 9.9
          AND s.list_date <= :min_list_date
          AND sd.vol > 0
    """)

    # raw_tushare_daily_basic 的 trade_date 是 String(8) 格式
    target_date_str = target_date.strftime("%Y%m%d")
    result = await session.execute(
        query, {
            "target_date": target_date,
            "target_date_str": target_date_str,
            "min_list_date": min_list_date,
        }
    )
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=result.keys())

    # 将所有 Decimal 列转为 float
    for col in df.columns:
        if col not in ["ts_code", "name", "trade_date"] and df[col].dtype == object:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # 前日技术指标（_prev 后缀）
    if prev_date is not None and not df.empty:
        ts_codes = df["ts_code"].tolist()
        codes_placeholder = ", ".join(f":c{i}" for i in range(len(ts_codes)))
        code_params = {f"c{i}": code for i, code in enumerate(ts_codes)}

        prev_sql = text(f"""
            SELECT
                td.ts_code,
                td.ma5 AS ma5_prev,
                td.ma20 AS ma20_prev,
                td.ma60 AS ma60_prev,
                td.macd_dif AS macd_dif_prev,
                td.atr14 AS atr14_prev,
                td.rsi6 AS rsi6_prev,
                td.rsi12 AS rsi12_prev,
                sd.close AS close_prev,
                sd.open AS open_prev,
                sd.pct_chg AS pct_chg_prev
            FROM technical_daily td
            JOIN stock_daily sd
                ON td.ts_code = sd.ts_code AND td.trade_date = sd.trade_date
            WHERE td.trade_date = :prev_date
              AND td.ts_code IN ({codes_placeholder})
        """)
        prev_result = await session.execute(
            prev_sql, {"prev_date": prev_date, **code_params}
        )
        prev_rows = prev_result.fetchall()

        if prev_rows:
            prev_columns = [
                "ts_code",
                "ma5_prev", "ma20_prev", "ma60_prev",
                "macd_dif_prev", "atr14_prev",
                "rsi6_prev", "rsi12_prev",
                "close_prev", "open_prev", "pct_chg_prev",
            ]
            prev_df = pd.DataFrame(prev_rows, columns=prev_columns)
            # Decimal → float
            for col in prev_df.columns:
                if col != "ts_code" and prev_df[col].dtype == object:
                    prev_df[col] = pd.to_numeric(prev_df[col], errors="coerce")
            df = df.merge(prev_df, on="ts_code", how="left")

    return df


async def _enrich_finance_data_v2(
    session: AsyncSession,
    df: pd.DataFrame,
    target_date: date,
) -> pd.DataFrame:
    """为 DataFrame 补充财务指标数据（V2 专用）。

    使用每只股票最新一期已公告的财务报告（ann_date <= target_date）。
    """
    if df.empty:
        return df

    ts_codes = df["ts_code"].tolist()
    codes_placeholder = ", ".join(f":c{i}" for i in range(len(ts_codes)))
    code_params = {f"c{i}": code for i, code in enumerate(ts_codes)}

    # 使用 DISTINCT ON 获取每只股票最新一期财务数据
    finance_sql = text(f"""
        SELECT DISTINCT ON (ts_code)
            ts_code,
            pe_ttm, pb, roe, eps,
            revenue_yoy, profit_yoy,
            current_ratio, quick_ratio, debt_ratio,
            gross_margin, net_margin,
            ocf_per_share
        FROM finance_indicator
        WHERE ts_code IN ({codes_placeholder})
          AND ann_date <= :target_date
        ORDER BY ts_code, end_date DESC
    """)

    result = await session.execute(
        finance_sql, {"target_date": target_date, **code_params}
    )
    rows = result.fetchall()

    if rows:
        fin_columns = [
            "ts_code", "pe_ttm", "pb", "roe", "eps",
            "revenue_yoy", "profit_yoy",
            "current_ratio", "quick_ratio", "debt_ratio",
            "gross_margin", "net_margin",
            "ocf_per_share",
        ]
        fin_df = pd.DataFrame(rows, columns=fin_columns)
        # Decimal → float
        for col in fin_df.columns:
            if col != "ts_code" and fin_df[col].dtype == object:
                fin_df[col] = pd.to_numeric(fin_df[col], errors="coerce")
        df = df.merge(fin_df, on="ts_code", how="left")

    # 从 raw_tushare_daily_basic 补充每日估值指标（dividend_yield 等）
    # daily_basic 的估值数据比 finance_indicator 更实时（每日更新），优先使用
    daily_basic_sql = text(f"""
        SELECT
            ts_code,
            pe_ttm AS db_pe_ttm,
            pb AS db_pb,
            dv_ttm AS dividend_yield
        FROM raw_tushare_daily_basic
        WHERE trade_date = :trade_date_str
          AND ts_code IN ({codes_placeholder})
    """)

    # raw_tushare_daily_basic 的 trade_date 是 String(8) 格式
    trade_date_str = target_date.strftime("%Y%m%d")
    db_result = await session.execute(
        daily_basic_sql, {"trade_date_str": trade_date_str, **code_params}
    )
    db_rows = db_result.fetchall()

    if db_rows:
        db_columns = ["ts_code", "db_pe_ttm", "db_pb", "dividend_yield"]
        db_df = pd.DataFrame(db_rows, columns=db_columns)
        # Decimal → float
        for col in db_df.columns:
            if col != "ts_code" and db_df[col].dtype == object:
                db_df[col] = pd.to_numeric(db_df[col], errors="coerce")
        df = df.merge(db_df, on="ts_code", how="left")

        # daily_basic 的估值指标覆盖 finance_indicator 的（更实时）
        for col, db_col in [("pe_ttm", "db_pe_ttm"), ("pb", "db_pb")]:
            if db_col in df.columns:
                if col in df.columns:
                    # 用 daily_basic 的值填充 finance_indicator 中的 NULL
                    df[col] = df[col].fillna(df[db_col])
                else:
                    df[col] = df[db_col]
                df.drop(columns=[db_col], inplace=True)

    logger.info(f"[Pipeline V2] 财务数据补充完成：{len(df)} 只股票")
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

    # 将 DataFrame 索引设置为 ts_code，方便后续查找
    df_indexed = df.set_index("ts_code")

    # 获取所有 Confirmer 策略
    confirmers = StrategyFactoryV2.get_by_role(StrategyRole.CONFIRMER)
    confirmer_data = {}
    for meta in confirmers:
        confirmer = meta.strategy_cls()
        # Confirmer 返回的 Series 索引已经是 ts_code（在各 Confirmer 中设置）
        bonus_series = await confirmer.execute(df, target_date)
        # 获取 confirmer 的适用信号组
        applicable_groups = getattr(confirmer, "applicable_groups", [])
        confirmer_data[meta.name] = {
            "bonus_series": bonus_series,
            "applicable_groups": applicable_groups,
        }

    # 计算每只股票的最终得分
    picks = []
    for ts_code, signals in signals_by_stock.items():
        layer1_result = layer1_dict.get(ts_code)
        if not layer1_result or not layer1_result.passed_guard:
            continue

        # 获取股票基本信息
        if ts_code not in df_indexed.index:
            continue
        stock_row = df_indexed.loc[ts_code]

        # 信号强度分：Σ(静态权重 × 置信度)
        signal_strength = sum(sig.static_weight * sig.confidence for sig in signals)

        # Confirmer 加分：按信号组过滤，叠加所有匹配的 confirmer，封顶 0.6
        # 获取该股票的所有信号组
        stock_signal_groups = {sig.signal_group for sig in signals}

        total_bonus = 0.0
        for confirmer_name, data in confirmer_data.items():
            bonus_series = data["bonus_series"]
            applicable_groups = data["applicable_groups"]

            # 如果 confirmer 没有限制信号组，或者股票信号组与 confirmer 适用组有交集
            if not applicable_groups or any(
                sg in applicable_groups for sg in stock_signal_groups
            ):
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
