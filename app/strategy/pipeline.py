"""策略执行管道：5 层漏斗筛选。

Layer 1: SQL 粗筛 — 剔除 ST/退市/停牌/低流动性
Layer 2: 技术指标初筛 — 运行技术面策略
Layer 3: 财务指标复筛 — 运行基本面策略
Layer 4: 综合排序 — 按策略命中数排序，取 Top N
Layer 5: AI 终审 — 调用 Gemini 进行综合分析和评分
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import date

import pandas as pd
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.strategy.factory import StrategyFactory

logger = logging.getLogger(__name__)


@dataclass
class StockPick:
    """单只股票的选股结果。"""

    ts_code: str
    name: str
    close: float
    pct_chg: float
    matched_strategies: list[str] = field(default_factory=list)
    match_count: int = 0
    ai_score: int | None = None
    ai_signal: str | None = None
    ai_summary: str | None = None


@dataclass
class PipelineResult:
    """Pipeline 执行结果。"""

    target_date: date
    picks: list[StockPick] = field(default_factory=list)
    layer_stats: dict[str, int] = field(default_factory=dict)
    elapsed_ms: int = 0
    ai_enabled: bool = False


# --- PLACEHOLDER FOR LAYER FUNCTIONS ---


async def _layer1_base_filter(
    session: AsyncSession,
    target_date: date,
    base_filter: dict | None = None,
) -> pd.DataFrame:
    """Layer 1: SQL 粗筛，获取当日可交易股票列表。

    剔除 ST/停牌/退市/低流动性股票。
    返回包含 ts_code, name 的 DataFrame。
    """
    opts = {
        "exclude_st": True,
        "min_turnover_rate": 0.001,
        **(base_filter or {}),
    }

    # 查询当日有交易的上市股票，JOIN stocks 表获取名称和状态
    sql = text("""
        SELECT
            sd.ts_code,
            s.name,
            sd.close,
            sd.pct_chg,
            sd.vol,
            sd.turnover_rate
        FROM stock_daily sd
        JOIN stocks s ON sd.ts_code = s.ts_code
        WHERE sd.trade_date = :target_date
          AND s.list_status = 'L'
          AND sd.vol > 0
          AND sd.turnover_rate >= :min_turnover
    """)

    params: dict = {
        "target_date": target_date,
        "min_turnover": opts["min_turnover_rate"],
    }

    result = await session.execute(sql, params)
    rows = result.fetchall()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["ts_code", "name", "close", "pct_chg", "vol", "turnover_rate"])

    # 剔除 ST 股票
    if opts.get("exclude_st", True):
        st_mask = df["name"].str.contains("ST", case=False, na=False)
        df = df[~st_mask].reset_index(drop=True)

    logger.info("Layer 1 粗筛完成：%d 只股票通过", len(df))
    return df


async def _build_market_snapshot(
    session: AsyncSession,
    ts_codes: list[str],
    target_date: date,
) -> pd.DataFrame:
    """构建市场快照 DataFrame。

    JOIN stock_daily + technical_daily（当日）+ technical_daily（前日，_prev 后缀）
    + finance_indicator（最新报告期）。
    """
    if not ts_codes:
        return pd.DataFrame()

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
    codes_placeholder = ", ".join(f":c{i}" for i in range(len(ts_codes)))
    code_params = {f"c{i}": code for i, code in enumerate(ts_codes)}

    current_sql = text(f"""
        SELECT
            sd.ts_code, sd.close, sd.pct_chg, sd.vol, sd.amount,
            sd.turnover_rate, sd.open, sd.high, sd.low,
            td.ma5, td.ma10, td.ma20, td.ma60, td.ma120, td.ma250,
            td.macd_dif, td.macd_dea, td.macd_hist,
            td.kdj_k, td.kdj_d, td.kdj_j,
            td.rsi6, td.rsi12, td.rsi24,
            td.boll_upper, td.boll_mid, td.boll_lower,
            td.vol_ma5, td.vol_ma10, td.vol_ratio,
            td.atr14,
            td.obv, td.donchian_upper, td.donchian_lower
        FROM stock_daily sd
        LEFT JOIN technical_daily td
            ON sd.ts_code = td.ts_code AND sd.trade_date = td.trade_date
        WHERE sd.trade_date = :target_date
          AND sd.ts_code IN ({codes_placeholder})
    """)

    result = await session.execute(
        current_sql, {"target_date": target_date, **code_params}
    )
    rows = result.fetchall()
    if not rows:
        return pd.DataFrame()

    columns = [
        "ts_code", "close", "pct_chg", "vol", "amount",
        "turnover_rate", "open", "high", "low",
        "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
        "macd_dif", "macd_dea", "macd_hist",
        "kdj_k", "kdj_d", "kdj_j",
        "rsi6", "rsi12", "rsi24",
        "boll_upper", "boll_mid", "boll_lower",
        "vol_ma5", "vol_ma10", "vol_ratio",
        "atr14",
        "obv", "donchian_upper", "donchian_lower",
    ]
    df = pd.DataFrame(rows, columns=columns)

    # 前日技术指标（_prev 后缀）
    if prev_date is not None:
        prev_sql = text(f"""
            SELECT
                td.ts_code,
                td.ma5 AS ma5_prev, td.ma10 AS ma10_prev,
                td.ma20 AS ma20_prev, td.ma60 AS ma60_prev,
                td.macd_dif AS macd_dif_prev, td.macd_dea AS macd_dea_prev,
                td.kdj_k AS kdj_k_prev, td.kdj_d AS kdj_d_prev,
                td.rsi6 AS rsi6_prev, td.rsi12 AS rsi12_prev,
                td.boll_lower AS boll_lower_prev,
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
                "ma5_prev", "ma10_prev", "ma20_prev", "ma60_prev",
                "macd_dif_prev", "macd_dea_prev",
                "kdj_k_prev", "kdj_d_prev",
                "rsi6_prev", "rsi12_prev",
                "boll_lower_prev", "close_prev",
                "open_prev", "pct_chg_prev",
            ]
            prev_df = pd.DataFrame(prev_rows, columns=prev_columns)
            df = df.merge(prev_df, on="ts_code", how="left")

    logger.info("市场快照构建完成：%d 只股票，%d 列", len(df), len(df.columns))
    return df


async def _enrich_finance_data(
    session: AsyncSession,
    df: pd.DataFrame,
    target_date: date,
) -> pd.DataFrame:
    """为 DataFrame 补充财务指标数据。

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
            gross_margin, net_margin
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
        ]
        fin_df = pd.DataFrame(rows, columns=fin_columns)
        df = df.merge(fin_df, on="ts_code", how="left")

    # 从 raw_tushare_daily_basic 补充每日估值指标（pe_ttm、pb、ps_ttm、dividend_yield 等）
    # daily_basic 的估值数据比 finance_indicator 更实时（每日更新），优先使用
    daily_basic_sql = text(f"""
        SELECT
            ts_code,
            pe_ttm AS db_pe_ttm,
            pb AS db_pb,
            ps_ttm AS db_ps_ttm,
            dv_ttm AS dividend_yield,
            total_mv AS db_total_mv,
            circ_mv AS db_circ_mv
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
        db_columns = [
            "ts_code", "db_pe_ttm", "db_pb", "db_ps_ttm",
            "dividend_yield", "db_total_mv", "db_circ_mv",
        ]
        db_df = pd.DataFrame(db_rows, columns=db_columns)
        df = df.merge(db_df, on="ts_code", how="left")

        # daily_basic 的估值指标覆盖 finance_indicator 的（更实时）
        for col, db_col in [
            ("pe_ttm", "db_pe_ttm"), ("pb", "db_pb"),
            ("ps_ttm", "db_ps_ttm"), ("total_mv", "db_total_mv"),
            ("circ_mv", "db_circ_mv"),
        ]:
            if db_col in df.columns:
                if col in df.columns:
                    # 用 daily_basic 的值填充 finance_indicator 中的 NULL
                    df[col] = df[col].fillna(df[db_col])
                else:
                    df[col] = df[db_col]
                df.drop(columns=[db_col], inplace=True)

    logger.info("财务数据补充完成：%d 只股票", len(df))
    return df


async def _run_strategies_on_df(
    df: pd.DataFrame,
    strategy_names: list[str],
    category: str,
    target_date: date,
    hit_records: dict[str, list[str]],
    strategy_params: dict[str, dict] | None = None,
) -> pd.DataFrame:
    """在 DataFrame 上运行指定分类的策略。

    Args:
        df: 市场快照 DataFrame
        strategy_names: 要运行的策略名称列表
        category: 筛选的策略分类（"technical" 或 "fundamental"）
        target_date: 目标日期
        hit_records: ts_code -> 命中策略名称列表（就地更新）
        strategy_params: 策略名称 -> 自定义参数字典（覆盖默认值）

    Returns:
        通过筛选的 DataFrame
    """
    # 筛选出属于指定分类的策略
    category_strategies = [
        name for name in strategy_names
        if StrategyFactory.get_meta(name).category == category
    ]

    if not category_strategies or df.empty:
        # 没有该分类的策略，全部通过
        return df

    # 运行每个策略，记录命中
    combined = pd.Series(False, index=df.index)

    for name in category_strategies:
        # 使用自定义参数实例化策略（如果有）
        custom_params = (strategy_params or {}).get(name)
        strategy = StrategyFactory.get_strategy(name, params=custom_params)
        try:
            mask = await strategy.filter_batch(df, target_date)
            # 记录命中的股票
            hit_codes = df.loc[mask, "ts_code"].tolist()
            for code in hit_codes:
                if code not in hit_records:
                    hit_records[code] = []
                if name not in hit_records[code]:
                    hit_records[code].append(name)
            combined = combined | mask
        except Exception:
            logger.exception("策略 %s 执行异常，跳过", name)

    passed_df = df[combined].reset_index(drop=True)

    logger.info(
        "Layer %s 筛选完成：%d -> %d 只股票（策略：%s）",
        category, len(df), len(passed_df), category_strategies,
    )
    return passed_df


def _layer4_rank_and_topn(
    df: pd.DataFrame,
    name_map: dict[str, str],
    hit_records: dict[str, list[str]],
    top_n: int,
) -> list[StockPick]:
    """Layer 4: 按命中策略数降序排序，取 Top N。

    Args:
        df: 通过 Layer 2-3 的 DataFrame
        name_map: ts_code -> 股票名称映射
        hit_records: ts_code -> 命中的策略名称列表
        top_n: 返回数量上限

    Returns:
        排序后的 StockPick 列表
    """
    if df.empty:
        return []

    picks: list[StockPick] = []
    for _, row in df.iterrows():
        ts_code = row["ts_code"]
        strategies = hit_records.get(ts_code, [])
        picks.append(StockPick(
            ts_code=ts_code,
            name=name_map.get(ts_code, ""),
            close=float(row.get("close", 0) or 0),
            pct_chg=float(row.get("pct_chg", 0) or 0),
            matched_strategies=strategies,
            match_count=len(strategies),
        ))

    # 按命中策略数降序排序
    picks.sort(key=lambda p: p.match_count, reverse=True)

    return picks[:top_n]


async def _layer5_ai_analysis(
    picks: list[StockPick],
    market_snapshot: pd.DataFrame,
    target_date: date,
) -> list[StockPick]:
    """Layer 5: AI 终审，调用 Gemini 进行综合分析和评分。

    未配置 API Key 或调用失败时静默降级，返回原始 picks。
    """
    from app.ai.manager import get_ai_manager

    ai_manager = get_ai_manager()

    if not ai_manager.is_enabled:
        logger.info("Layer 5 AI 未启用，透传 %d 只股票", len(picks))
        return picks

    # 从 market_snapshot 构建 market_data 字典
    market_data: dict[str, dict] = {}
    if not market_snapshot.empty:
        for _, row in market_snapshot.iterrows():
            ts_code = row.get("ts_code")
            if ts_code:
                market_data[ts_code] = {
                    k: v for k, v in row.to_dict().items()
                    if k != "ts_code" and v is not None and not (isinstance(v, float) and v != v)
                }

    logger.info("Layer 5 AI 分析：%d 只股票", len(picks))
    return await ai_manager.analyze(picks, market_data, target_date)


async def execute_pipeline(
    session_factory: async_sessionmaker,
    strategy_names: list[str],
    target_date: date,
    base_filter: dict | None = None,
    top_n: int = 30,
    strategy_params: dict[str, dict] | None = None,
) -> PipelineResult:
    """执行完整的 5 层选股管道。

    Args:
        session_factory: 异步数据库会话工厂
        strategy_names: 要运行的策略名称列表
        target_date: 筛选日期
        base_filter: Layer 1 过滤参数覆盖
        top_n: 最终返回的股票数量上限
        strategy_params: 策略名称 -> 自定义参数字典（覆盖默认值）

    Returns:
        PipelineResult 包含选股结果和各层统计
    """
    start_time = time.monotonic()
    layer_stats: dict[str, int] = {}

    # 空策略列表直接返回
    if not strategy_names:
        elapsed = int((time.monotonic() - start_time) * 1000)
        return PipelineResult(
            target_date=target_date,
            picks=[],
            layer_stats=layer_stats,
            elapsed_ms=elapsed,
            ai_enabled=False,
        )

    async with session_factory() as session:
        # Layer 1: SQL 粗筛
        layer1_df = await _layer1_base_filter(session, target_date, base_filter)
        layer_stats["layer1"] = len(layer1_df)

        if layer1_df.empty:
            elapsed = int((time.monotonic() - start_time) * 1000)
            return PipelineResult(
                target_date=target_date,
                picks=[],
                layer_stats=layer_stats,
                elapsed_ms=elapsed,
                ai_enabled=False,
            )

        # 保存 ts_code -> name 映射
        name_map = dict(zip(layer1_df["ts_code"], layer1_df["name"]))

        # 构建市场快照（技术指标 + 前日数据）
        snapshot_df = await _build_market_snapshot(
            session, layer1_df["ts_code"].tolist(), target_date
        )

        # 补充 name 列（从 layer1_df 获取）
        if not snapshot_df.empty:
            name_series = layer1_df[["ts_code", "name"]].drop_duplicates("ts_code")
            snapshot_df = snapshot_df.merge(name_series, on="ts_code", how="left")

        # Layer 2: 技术面策略筛选
        hit_records: dict[str, list[str]] = {}
        layer2_df = await _run_strategies_on_df(
            snapshot_df, strategy_names, "technical", target_date, hit_records,
            strategy_params=strategy_params,
        )
        layer_stats["layer2"] = len(layer2_df)

        # 补充财务数据
        if not layer2_df.empty:
            layer2_df = await _enrich_finance_data(
                session, layer2_df, target_date
            )

        # Layer 3: 基本面策略筛选
        layer3_df = await _run_strategies_on_df(
            layer2_df, strategy_names, "fundamental", target_date, hit_records,
            strategy_params=strategy_params,
        )
        layer_stats["layer3"] = len(layer3_df)

    # Layer 4: 排序取 Top N
    picks = _layer4_rank_and_topn(layer3_df, name_map, hit_records, top_n)
    layer_stats["layer4"] = len(picks)

    # Layer 5: AI 分析
    from app.ai.manager import get_ai_manager

    ai_enabled = get_ai_manager().is_enabled
    picks = await _layer5_ai_analysis(picks, snapshot_df, target_date)

    elapsed = int((time.monotonic() - start_time) * 1000)
    logger.info(
        "Pipeline 执行完成：%d ms，各层统计 %s",
        elapsed, layer_stats,
    )

    return PipelineResult(
        target_date=target_date,
        picks=picks,
        layer_stats=layer_stats,
        elapsed_ms=elapsed,
        ai_enabled=ai_enabled,
    )
