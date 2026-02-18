"""技术指标计算引擎。

基于 pandas 向量化计算所有技术指标，支持多种市场数据表：
- stock_daily → technical_daily（股票技术指标）
- index_daily → index_technical_daily（指数技术指标）
- concept_daily → concept_technical_daily（板块技术指标）

支持单标的计算、全市场批量计算和增量更新。

指标列表（共 29 个）：
- 均线：MA5, MA10, MA20, MA60, MA120, MA250
- MACD：DIF, DEA, HIST
- KDJ：K, D, J
- RSI：RSI6, RSI12, RSI24
- 布林带：BOLL_UPPER, BOLL_MID, BOLL_LOWER
- 成交量：VOL_MA5, VOL_MA10, VOL_RATIO
- 波动率：ATR14
- 扩展指标：WR, CCI, BIAS, OBV, DONCHIAN_UPPER, DONCHIAN_LOWER
"""

import logging
import time
from collections.abc import Callable
from datetime import date
from typing import Any, Type

import numpy as np
import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.models.concept import ConceptDaily, ConceptTechnicalDaily
from app.models.index import IndexDaily, IndexTechnicalDaily
from app.models.market import Stock, StockDaily
from app.models.technical import TechnicalDaily

logger = logging.getLogger(__name__)

# 计算指标所需的最大历史窗口天数（MA250 需要 250 天 + 余量）
LOOKBACK_DAYS = 300

# 批量提交的股票数量
BATCH_COMMIT_SIZE = 100

# ============================================================
# 单指标计算函数
# ============================================================


def _compute_ma(close: pd.Series, period: int) -> pd.Series:
    """计算简单移动平均线 (SMA)。

    公式：MA(N) = sum(close[-N:]) / N

    Args:
        close: 收盘价序列
        period: 均线周期

    Returns:
        移动平均线序列，数据不足的位置为 NaN
    """
    return close.rolling(window=period, min_periods=period).mean()


def _compute_ema(series: pd.Series, period: int) -> pd.Series:
    """计算指数移动平均线 (EMA)。

    公式：EMA(t) = value(t) * α + EMA(t-1) * (1 - α)
    其中 α = 2 / (period + 1)

    Args:
        series: 输入数据序列
        period: EMA 周期

    Returns:
        EMA 序列
    """
    return series.ewm(span=period, adjust=False).mean()


def _compute_macd(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """计算 MACD 指标（参数 12, 26, 9）。

    - DIF = EMA(close, 12) - EMA(close, 26)
    - DEA = EMA(DIF, 9)
    - HIST = 2 * (DIF - DEA)

    Args:
        close: 收盘价序列

    Returns:
        (macd_dif, macd_dea, macd_hist) 三元组
    """
    ema12 = _compute_ema(close, 12)
    ema26 = _compute_ema(close, 26)
    dif = ema12 - ema26
    dea = _compute_ema(dif, 9)
    hist = 2.0 * (dif - dea)
    return dif, dea, hist


def _compute_kdj(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> tuple[pd.Series, pd.Series, pd.Series]:
    """计算 KDJ 指标（参数 9, 3, 3）。

    1. RSV = (close - lowest_low(9)) / (highest_high(9) - lowest_low(9)) * 100
    2. K = EMA(RSV, 3)，初始值 50
    3. D = EMA(K, 3)，初始值 50
    4. J = 3K - 2D

    当最高价等于最低价时，RSV 设为 50（避免除零）。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列

    Returns:
        (kdj_k, kdj_d, kdj_j) 三元组
    """
    # 9 日最高价和最低价
    lowest_low = low.rolling(window=9, min_periods=9).min()
    highest_high = high.rolling(window=9, min_periods=9).max()

    # 计算 RSV，处理除零情况
    price_range = highest_high - lowest_low
    rsv = pd.Series(np.where(
        price_range == 0,
        50.0,  # 最高价等于最低价时 RSV 设为 50
        (close - lowest_low) / price_range * 100.0,
    ), index=close.index)

    # 使用递推方式计算 K 和 D（初始值 50）
    k_values = np.full(len(close), np.nan)
    d_values = np.full(len(close), np.nan)

    # 找到第一个有效 RSV 的位置
    first_valid = rsv.first_valid_index()
    if first_valid is None:
        return (
            pd.Series(np.nan, index=close.index),
            pd.Series(np.nan, index=close.index),
            pd.Series(np.nan, index=close.index),
        )

    first_pos = close.index.get_loc(first_valid)
    k_values[first_pos] = 50.0 * 2 / 3 + rsv.iloc[first_pos] / 3
    d_values[first_pos] = 50.0 * 2 / 3 + k_values[first_pos] / 3

    for i in range(first_pos + 1, len(close)):
        if np.isnan(rsv.iloc[i]):
            continue
        k_values[i] = k_values[i - 1] * 2 / 3 + rsv.iloc[i] / 3
        d_values[i] = d_values[i - 1] * 2 / 3 + k_values[i] / 3

    k_series = pd.Series(k_values, index=close.index)
    d_series = pd.Series(d_values, index=close.index)
    j_series = 3.0 * k_series - 2.0 * d_series

    return k_series, d_series, j_series


def _compute_rsi(close: pd.Series, period: int) -> pd.Series:
    """计算 RSI（相对强弱指标），使用 Wilder 平滑法。

    1. delta = close - close.shift(1)
    2. gain = max(delta, 0), loss = abs(min(delta, 0))
    3. avg_gain = Wilder EMA(gain, N), avg_loss = Wilder EMA(loss, N)
    4. RS = avg_gain / avg_loss
    5. RSI = 100 - 100 / (1 + RS)

    当 avg_loss == 0 时 RSI = 100；当 avg_gain == 0 时 RSI = 0。

    Args:
        close: 收盘价序列
        period: RSI 周期（6, 12, 24）

    Returns:
        RSI 序列，值域 [0, 100]
    """
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)

    # Wilder 平滑：alpha = 1/period（等价于 com=period-1）
    avg_gain = gain.ewm(com=period - 1, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100.0 - 100.0 / (1.0 + rs)

    # 处理边界：avg_loss 为 0 时 RS 为 inf，RSI 应为 100
    # avg_gain 为 0 时 RS 为 0，RSI 应为 0
    # pandas 自动处理：inf -> 100, 0/0 -> NaN
    rsi = rsi.where(avg_loss != 0, 100.0)
    rsi = rsi.where(~((avg_gain == 0) & (avg_loss == 0)), 0.0)

    return rsi


def _compute_boll(close: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """计算布林带指标（参数 20, 2）。

    - BOLL_MID = MA(close, 20)
    - BOLL_UPPER = BOLL_MID + 2 * STD(close, 20)
    - BOLL_LOWER = BOLL_MID - 2 * STD(close, 20)

    使用总体标准差（ddof=0）。

    Args:
        close: 收盘价序列

    Returns:
        (boll_upper, boll_mid, boll_lower) 三元组
    """
    mid = close.rolling(window=20, min_periods=20).mean()
    std = close.rolling(window=20, min_periods=20).std(ddof=0)
    upper = mid + 2.0 * std
    lower = mid - 2.0 * std
    return upper, mid, lower


def _compute_vol_indicators(vol: pd.Series) -> tuple[pd.Series, pd.Series, pd.Series]:
    """计算成交量相关指标。

    - vol_ma5: 5 日成交量均线
    - vol_ma10: 10 日成交量均线
    - vol_ratio: 当日成交量 / vol_ma5（量比）

    当 vol_ma5 为 0 时，vol_ratio 设为 NaN。

    Args:
        vol: 成交量序列

    Returns:
        (vol_ma5, vol_ma10, vol_ratio) 三元组
    """
    vol_ma5 = vol.rolling(window=5, min_periods=5).mean()
    vol_ma10 = vol.rolling(window=10, min_periods=10).mean()
    # 量比：当日成交量 / 5日均量，vol_ma5 为 0 时结果为 NaN
    vol_ratio = vol / vol_ma5.replace(0, np.nan)
    return vol_ma5, vol_ma10, vol_ratio


def _compute_wr(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """计算 Williams %R 指标。

    公式：WR = (HH(N) - close) / (HH(N) - LL(N)) * -100
    值域 [-100, 0]，低于 -80 为超卖，高于 -20 为超买。
    当最高价等于最低价时，WR 设为 -50。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 回看周期，默认 14

    Returns:
        Williams %R 序列
    """
    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()
    price_range = highest_high - lowest_low
    wr = pd.Series(
        np.where(price_range == 0, -50.0, (highest_high - close) / price_range * -100.0),
        index=close.index,
    )
    # 数据不足时保持 NaN
    wr = wr.where(highest_high.notna(), np.nan)
    return wr


def _compute_cci(
    high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14
) -> pd.Series:
    """计算 CCI（商品通道指标）。

    公式：
    TP = (high + low + close) / 3
    CCI = (TP - SMA(TP, N)) / (0.015 * MAD(TP, N))

    当 MAD 为 0 时，CCI 设为 0。

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列
        period: 回看周期，默认 14

    Returns:
        CCI 序列
    """
    tp = (high + low + close) / 3.0
    tp_sma = tp.rolling(window=period, min_periods=period).mean()
    # 平均绝对偏差 (MAD)
    mad = tp.rolling(window=period, min_periods=period).apply(
        lambda x: np.abs(x - x.mean()).mean(), raw=True
    )
    cci = (tp - tp_sma) / (0.015 * mad)
    # MAD 为 0 时 CCI 设为 0
    cci = cci.where(mad != 0, 0.0)
    return cci


def _compute_bias(close: pd.Series, ma20: pd.Series) -> pd.Series:
    """计算 BIAS 乖离率（基于 MA20）。

    公式：BIAS = (close - MA20) / MA20 * 100

    当 MA20 为 NaN 或 0 时，BIAS 为 NaN。

    Args:
        close: 收盘价序列
        ma20: 20 日均线序列

    Returns:
        BIAS 序列
    """
    ma20_safe = ma20.replace(0, np.nan)
    return (close - ma20_safe) / ma20_safe * 100.0


def _compute_obv(close: pd.Series, vol: pd.Series) -> pd.Series:
    """计算 OBV（能量潮）。

    公式：OBV(t) = OBV(t-1) + sign(close(t) - close(t-1)) * vol(t)
    OBV(0) = 0，价格不变时 vol 贡献为 0。

    Args:
        close: 收盘价序列
        vol: 成交量序列

    Returns:
        OBV 序列
    """
    price_change = close.diff()
    direction = np.sign(price_change)
    obv = (direction * vol).fillna(0).cumsum()
    return obv


def _compute_donchian(
    high: pd.Series, low: pd.Series, period: int = 20
) -> tuple[pd.Series, pd.Series]:
    """计算唐奇安通道（不含当日）。

    donchian_upper = 过去 N 日最高价（不含当日）
    donchian_lower = 过去 N 日最低价（不含当日）

    Args:
        high: 最高价序列
        low: 最低价序列
        period: 回看周期，默认 20

    Returns:
        (donchian_upper, donchian_lower) 二元组
    """
    # shift(1) 排除当日，然后取 N 日窗口
    donchian_upper = high.shift(1).rolling(window=period, min_periods=period).max()
    donchian_lower = low.shift(1).rolling(window=period, min_periods=period).min()
    return donchian_upper, donchian_lower


def _compute_atr(
    high: pd.Series, low: pd.Series, close: pd.Series
) -> pd.Series:
    """计算 ATR（平均真实波幅），周期 14。

    1. True Range = max(high - low, abs(high - prev_close), abs(low - prev_close))
    2. ATR14 = EMA(True Range, 14)

    Args:
        high: 最高价序列
        low: 最低价序列
        close: 收盘价序列

    Returns:
        ATR14 序列
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.ewm(span=14, adjust=False, min_periods=14).mean()
    return atr


# ============================================================
# 核心入口：泛化指标计算（支持多种市场数据表）
# ============================================================


def compute_indicators_generic(df: pd.DataFrame) -> pd.DataFrame:
    """计算单个标的的全部 23 个技术指标（泛化版本）。

    适用于任何包含 OHLCV 数据的 DataFrame（股票、指数、板块）。
    输入 DataFrame 必须包含以下列（按 trade_date 升序排列）：
    trade_date, open, high, low, close, vol

    输出 DataFrame 在原始列基础上新增 23 个指标列。
    数据不足的行对应指标值为 NaN。

    Args:
        df: 单个标的的日线数据 DataFrame

    Returns:
        包含所有指标列的 DataFrame
    """
    if df.empty:
        # 返回空 DataFrame，包含所有指标列
        indicator_cols = [
            "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
            "macd_dif", "macd_dea", "macd_hist",
            "kdj_k", "kdj_d", "kdj_j",
            "rsi6", "rsi12", "rsi24",
            "boll_upper", "boll_mid", "boll_lower",
            "vol_ma5", "vol_ma10", "vol_ratio",
            "atr14",
            "wr", "cci", "bias", "obv",
            "donchian_upper", "donchian_lower",
        ]
        for col in indicator_cols:
            df[col] = pd.Series(dtype="float64")
        return df

    result = df.copy()
    close = result["close"].astype(float)
    high = result["high"].astype(float)
    low = result["low"].astype(float)
    vol = result["vol"].astype(float)

    # 记录各指标计算耗时
    indicator_times = {}

    # --- 均线 ---
    ma_start = time.time()
    for period in (5, 10, 20, 60, 120, 250):
        result[f"ma{period}"] = _compute_ma(close, period)
    indicator_times["MA"] = time.time() - ma_start

    # --- MACD ---
    macd_start = time.time()
    result["macd_dif"], result["macd_dea"], result["macd_hist"] = _compute_macd(close)
    indicator_times["MACD"] = time.time() - macd_start

    # --- KDJ ---
    kdj_start = time.time()
    result["kdj_k"], result["kdj_d"], result["kdj_j"] = _compute_kdj(high, low, close)
    indicator_times["KDJ"] = time.time() - kdj_start

    # --- RSI ---
    rsi_start = time.time()
    for period in (6, 12, 24):
        result[f"rsi{period}"] = _compute_rsi(close, period)
    indicator_times["RSI"] = time.time() - rsi_start

    # --- 布林带 ---
    boll_start = time.time()
    result["boll_upper"], result["boll_mid"], result["boll_lower"] = _compute_boll(close)
    indicator_times["BOLL"] = time.time() - boll_start

    # --- 成交量指标 ---
    vol_start = time.time()
    result["vol_ma5"], result["vol_ma10"], result["vol_ratio"] = _compute_vol_indicators(vol)
    indicator_times["VOL"] = time.time() - vol_start

    # --- ATR ---
    atr_start = time.time()
    result["atr14"] = _compute_atr(high, low, close)
    indicator_times["ATR"] = time.time() - atr_start

    # --- Williams %R ---
    wr_start = time.time()
    result["wr"] = _compute_wr(high, low, close, period=14)
    indicator_times["WR"] = time.time() - wr_start

    # --- CCI ---
    cci_start = time.time()
    result["cci"] = _compute_cci(high, low, close, period=14)
    indicator_times["CCI"] = time.time() - cci_start

    # --- BIAS（依赖 MA20，需在均线之后计算） ---
    bias_start = time.time()
    result["bias"] = _compute_bias(close, result["ma20"])
    indicator_times["BIAS"] = time.time() - bias_start

    # --- OBV ---
    obv_start = time.time()
    result["obv"] = _compute_obv(close, vol)
    indicator_times["OBV"] = time.time() - obv_start

    # --- 唐奇安通道 ---
    donchian_start = time.time()
    result["donchian_upper"], result["donchian_lower"] = _compute_donchian(high, low, period=20)
    indicator_times["DONCHIAN"] = time.time() - donchian_start

    # 记录总耗时和慢速指标（DEBUG 级别）
    total_time = sum(indicator_times.values())
    logger.debug(
        "[compute_indicators] 总耗时=%.3fs, MA=%.3fs, MACD=%.3fs, KDJ=%.3fs, RSI=%.3fs, "
        "BOLL=%.3fs, VOL=%.3fs, ATR=%.3fs, WR=%.3fs, CCI=%.3fs, BIAS=%.3fs, OBV=%.3fs, DONCHIAN=%.3fs",
        total_time, indicator_times["MA"], indicator_times["MACD"], indicator_times["KDJ"],
        indicator_times["RSI"], indicator_times["BOLL"], indicator_times["VOL"], indicator_times["ATR"],
        indicator_times["WR"], indicator_times["CCI"], indicator_times["BIAS"],
        indicator_times["OBV"], indicator_times["DONCHIAN"],
    )

    # 检测慢速指标（>0.1 秒）
    for name, elapsed in indicator_times.items():
        if elapsed > 0.1:
            logger.warning("[compute_indicators] 慢速指标：%s 耗时 %.3fs", name, elapsed)

    return result


# ============================================================
# 核心入口：单股票指标计算（向后兼容）
# ============================================================


def compute_single_stock_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算单只股票的全部 23 个技术指标。

    输入 DataFrame 必须包含以下列（按 trade_date 升序排列）：
    trade_date, open, high, low, close, vol

    输出 DataFrame 在原始列基础上新增 23 个指标列。
    数据不足的行对应指标值为 NaN。

    Args:
        df: 单只股票的日线数据 DataFrame

    Returns:
        包含所有指标列的 DataFrame

    Note:
        此函数为向后兼容保留，内部调用 compute_indicators_generic。
    """
    return compute_indicators_generic(df)


# ============================================================
# 数据库写入辅助
# ============================================================

# technical_daily 表中的指标列名（与 TechnicalDaily 模型对应）
INDICATOR_COLUMNS = [
    "ma5", "ma10", "ma20", "ma60", "ma120", "ma250",
    "macd_dif", "macd_dea", "macd_hist",
    "kdj_k", "kdj_d", "kdj_j",
    "rsi6", "rsi12", "rsi24",
    "boll_upper", "boll_mid", "boll_lower",
    "vol_ma5", "vol_ma10", "vol_ratio",
    "atr14",
    "wr", "cci", "bias", "obv",
    "donchian_upper", "donchian_lower",
]


async def _upsert_technical_rows(
    session: AsyncSession,
    rows: list[dict],
) -> int:
    """将技术指标数据 UPSERT 到 technical_daily 表。

    使用 PostgreSQL 的 INSERT ... ON CONFLICT DO UPDATE 实现幂等写入。
    自动分片以适配 asyncpg 32767 参数限制。

    Args:
        session: 异步数据库会话
        rows: 待写入的行数据列表，每行包含 ts_code, trade_date 和指标列

    Returns:
        处理的行数

    Note:
        此函数为向后兼容保留，内部调用 _upsert_technical_rows_generic。
    """
    return await _upsert_technical_rows_generic(session, rows, TechnicalDaily)


def _build_indicator_row(ts_code: str, trade_date: date, row: pd.Series) -> dict:
    """从计算结果的一行构建数据库写入字典。

    将 NaN 转换为 None（数据库 NULL）。

    Args:
        ts_code: 股票代码
        trade_date: 交易日期
        row: 包含指标值的 pandas Series

    Returns:
        可直接写入数据库的字典
    """
    record: dict = {"ts_code": ts_code, "trade_date": trade_date}
    for col in INDICATOR_COLUMNS:
        val = row.get(col)
        if val is not None and pd.notna(val):
            record[col] = round(float(val), 4)
        else:
            record[col] = None
    return record


async def _upsert_technical_rows_generic(
    session: AsyncSession,
    rows: list[dict],
    target_table: Type[DeclarativeBase],
) -> int:
    """将技术指标数据 UPSERT 到指定技术指标表（泛化版本）。

    使用 PostgreSQL 的 INSERT ... ON CONFLICT DO UPDATE 实现幂等写入。
    自动分片以适配 asyncpg 32767 参数限制。

    Args:
        session: 异步数据库会话
        rows: 待写入的行数据列表，每行包含 ts_code, trade_date 和指标列
        target_table: 目标技术指标表模型（TechnicalDaily/IndexTechnicalDaily/ConceptTechnicalDaily）

    Returns:
        处理的行数
    """
    if not rows:
        return 0

    from sqlalchemy.dialects.postgresql import insert as pg_insert

    table = target_table.__table__

    # asyncpg 参数上限 32767，每行列数 = ts_code + trade_date + 指标列
    cols_per_row = 2 + len(INDICATOR_COLUMNS)
    chunk_size = 32767 // cols_per_row

    for i in range(0, len(rows), chunk_size):
        chunk = rows[i : i + chunk_size]
        stmt = pg_insert(table).values(chunk)
        update_dict = {col: stmt.excluded[col] for col in INDICATOR_COLUMNS}
        update_dict["updated_at"] = text("NOW()")
        stmt = stmt.on_conflict_do_update(
            index_elements=["ts_code", "trade_date"],
            set_=update_dict,
        )
        await session.execute(stmt)

    return len(rows)


# ============================================================
# 全市场批量计算
# ============================================================


async def compute_all_stocks(
    session_factory: async_sessionmaker[AsyncSession],
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """全市场批量计算技术指标并写入 technical_daily 表。

    遍历所有上市股票，逐股加载历史日线数据，计算全部指标，
    使用 UPSERT 写入数据库。每 BATCH_COMMIT_SIZE 只股票提交一次。

    Args:
        session_factory: 异步数据库会话工厂
        progress_callback: 可选的进度回调函数，接收 (processed, total) 参数

    Returns:
        汇总字典：{"total": N, "success": M, "failed": F, "elapsed_seconds": T}
    """
    start_time = time.time()

    # 1. 查询所有上市股票代码
    async with session_factory() as session:
        stmt = select(Stock.ts_code).where(Stock.list_status == "L")
        result = await session.execute(stmt)
        all_codes = [row[0] for row in result.all()]

    total = len(all_codes)
    success = 0
    failed = 0
    logger.info("开始全量计算技术指标，共 %d 只股票", total)

    # 2. 逐股计算，分批提交
    batch_rows: list[dict] = []
    batch_count = 0

    for i, ts_code in enumerate(all_codes):
        try:
            # 加载该股票的历史日线数据
            async with session_factory() as session:
                stmt = (
                    select(StockDaily)
                    .where(StockDaily.ts_code == ts_code)
                    .order_by(StockDaily.trade_date.asc())
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                # 无日线数据，跳过
                logger.debug("股票 %s 无日线数据，跳过", ts_code)
                continue

            # 转换为 DataFrame
            records = [{
                "trade_date": r.trade_date,
                "open": float(r.open) if r.open else 0.0,
                "high": float(r.high) if r.high else 0.0,
                "low": float(r.low) if r.low else 0.0,
                "close": float(r.close) if r.close else 0.0,
                "vol": float(r.vol) if r.vol else 0.0,
            } for r in rows]
            df = pd.DataFrame(records)

            # 计算指标
            df_with_indicators = compute_single_stock_indicators(df)

            # 构建写入行（所有交易日的指标）
            for _, row in df_with_indicators.iterrows():
                batch_rows.append(
                    _build_indicator_row(ts_code, row["trade_date"], row)
                )

            success += 1

        except Exception as e:
            logger.error("计算股票 %s 指标失败: %s", ts_code, e)
            failed += 1

        batch_count += 1

        # 每 BATCH_COMMIT_SIZE 只股票提交一次
        if batch_count >= BATCH_COMMIT_SIZE and batch_rows:
            async with session_factory() as session:
                await _upsert_technical_rows(session, batch_rows)
                await session.commit()
            logger.info(
                "已提交 %d 只股票的指标数据（%d 行）",
                batch_count, len(batch_rows),
            )
            batch_rows = []
            batch_count = 0

        # 进度回调
        if progress_callback and (i + 1) % 500 == 0:
            progress_callback(i + 1, total)

    # 提交剩余数据
    if batch_rows:
        async with session_factory() as session:
            await _upsert_technical_rows(session, batch_rows)
            await session.commit()

    elapsed = round(time.time() - start_time, 2)
    summary = {
        "total": total,
        "success": success,
        "failed": failed,
        "elapsed_seconds": elapsed,
    }

    # 记录总体汇总日志
    avg_time = elapsed / total if total > 0 else 0
    logger.info(
        "[技术指标] 全量计算完成：成功 %d 只，失败 %d 只，总耗时 %.1fs，平均 %.3fs/只",
        success, failed, elapsed, avg_time,
    )

    # 检测慢速计算（总耗时 >30 分钟）
    if elapsed > 1800:
        logger.warning("[技术指标] 慢速计算：全量计算耗时 %.1fs (%.1f分钟)", elapsed, elapsed / 60)

    return summary


# ============================================================
# 增量计算（仅最新交易日）
# ============================================================


async def compute_incremental(
    session_factory: async_sessionmaker[AsyncSession],
    target_date: date | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """增量计算技术指标：仅计算指定交易日（默认最新）的指标。

    对每只股票加载 LOOKBACK_DAYS 天历史数据，计算指标后仅
    UPSERT 目标日期那一行到 technical_daily。

    Args:
        session_factory: 异步数据库会话工厂
        target_date: 目标交易日，None 表示自动检测最新交易日
        progress_callback: 可选的进度回调函数

    Returns:
        汇总字典：{"trade_date": "YYYY-MM-DD", "total": N, "success": M, "failed": F}
    """
    start_time = time.time()

    # 1. 确定目标交易日
    if target_date is None:
        async with session_factory() as session:
            result = await session.execute(
                select(StockDaily.trade_date)
                .order_by(StockDaily.trade_date.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                logger.warning("stock_daily 表无数据，无法确定最新交易日")
                return {"trade_date": None, "total": 0, "success": 0, "failed": 0}
            target_date = row

    logger.info("增量计算目标日期: %s", target_date)

    # 2. 查询在目标日期有日线数据的所有股票
    async with session_factory() as session:
        stmt = (
            select(StockDaily.ts_code)
            .where(StockDaily.trade_date == target_date)
            .distinct()
        )
        result = await session.execute(stmt)
        target_codes = [row[0] for row in result.all()]

    total = len(target_codes)
    success = 0
    failed = 0
    batch_rows: list[dict] = []
    batch_count = 0

    logger.info("目标日期 %s 共 %d 只股票需要计算", target_date, total)

    for i, ts_code in enumerate(target_codes):
        try:
            # 加载历史数据（截止到目标日期）
            async with session_factory() as session:
                stmt = (
                    select(StockDaily)
                    .where(
                        StockDaily.ts_code == ts_code,
                        StockDaily.trade_date <= target_date,
                    )
                    .order_by(StockDaily.trade_date.desc())
                    .limit(LOOKBACK_DAYS)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                continue

            # 转换为 DataFrame（注意：查询是 DESC 排序，需要反转）
            records = [{
                "trade_date": r.trade_date,
                "open": float(r.open) if r.open else 0.0,
                "high": float(r.high) if r.high else 0.0,
                "low": float(r.low) if r.low else 0.0,
                "close": float(r.close) if r.close else 0.0,
                "vol": float(r.vol) if r.vol else 0.0,
            } for r in reversed(rows)]
            df = pd.DataFrame(records)

            # 计算指标
            df_with_indicators = compute_single_stock_indicators(df)

            # 仅取目标日期那一行
            target_row = df_with_indicators[
                df_with_indicators["trade_date"] == target_date
            ]
            if not target_row.empty:
                batch_rows.append(
                    _build_indicator_row(ts_code, target_date, target_row.iloc[0])
                )

            success += 1

        except Exception as e:
            logger.error("增量计算股票 %s 指标失败: %s", ts_code, e)
            failed += 1

        batch_count += 1

        # 每 BATCH_COMMIT_SIZE 只股票提交一次
        if batch_count >= BATCH_COMMIT_SIZE and batch_rows:
            async with session_factory() as session:
                await _upsert_technical_rows(session, batch_rows)
                await session.commit()
            batch_rows = []
            batch_count = 0

        # 进度回调
        if progress_callback and (i + 1) % 500 == 0:
            progress_callback(i + 1, total)

    # 提交剩余数据
    if batch_rows:
        async with session_factory() as session:
            await _upsert_technical_rows(session, batch_rows)
            await session.commit()

    elapsed = round(time.time() - start_time, 2)
    summary = {
        "trade_date": str(target_date),
        "total": total,
        "success": success,
        "failed": failed,
        "elapsed_seconds": elapsed,
    }

    # 记录总体汇总日志
    avg_time = elapsed / total if total > 0 else 0
    logger.info(
        "[技术指标] 增量计算完成：日期 %s，成功 %d 只，失败 %d 只，总耗时 %.1fs，平均 %.3fs/只",
        target_date, success, failed, elapsed, avg_time,
    )

    # 检测慢速计算（总耗时 >10 分钟）
    if elapsed > 600:
        logger.warning("[技术指标] 慢速计算：增量计算耗时 %.1fs (%.1f分钟)", elapsed, elapsed / 60)

    return summary


# ============================================================
# 泛化批量计算和增量计算（支持多种市场数据表）
# ============================================================


async def compute_all_generic(
    session_factory: async_sessionmaker[AsyncSession],
    source_table: Type[DeclarativeBase],
    target_table: Type[DeclarativeBase],
    code_filter_column: str = "list_status",
    code_filter_value: str = "L",
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """泛化全市场批量计算技术指标并写入指定技术指标表。

    遍历所有标的，逐个加载历史日线数据，计算全部指标，
    使用 UPSERT 写入数据库。每 BATCH_COMMIT_SIZE 个标的提交一次。

    Args:
        session_factory: 异步数据库会话工厂
        source_table: 源数据表模型（StockDaily/IndexDaily/ConceptDaily）
        target_table: 目标技术指标表模型（TechnicalDaily/IndexTechnicalDaily/ConceptTechnicalDaily）
        code_filter_column: 用于过滤标的的列名（如 "list_status"）
        code_filter_value: 过滤值（如 "L" 表示上市）
        progress_callback: 可选的进度回调函数，接收 (processed, total) 参数

    Returns:
        汇总字典：{"total": N, "success": M, "failed": F, "elapsed_seconds": T}
    """
    start_time = time.time()

    # 1. 查询所有标的代码
    async with session_factory() as session:
        if code_filter_column and code_filter_value:
            # 对于股票，从 Stock 表查询上市股票
            if source_table == StockDaily:
                stmt = select(Stock.ts_code).where(getattr(Stock, code_filter_column) == code_filter_value)
            else:
                # 对于指数和板块，直接从源表查询所有唯一代码
                stmt = select(source_table.ts_code).distinct()
        else:
            stmt = select(source_table.ts_code).distinct()

        result = await session.execute(stmt)
        all_codes = [row[0] for row in result.all()]

    total = len(all_codes)
    success = 0
    failed = 0
    logger.info("开始全量计算技术指标（%s → %s），共 %d 个标的",
                source_table.__tablename__, target_table.__tablename__, total)

    # 2. 逐个计算，分批提交
    batch_rows: list[dict] = []
    batch_count = 0

    for i, ts_code in enumerate(all_codes):
        try:
            # 加载该标的的历史日线数据
            async with session_factory() as session:
                stmt = (
                    select(source_table)
                    .where(source_table.ts_code == ts_code)
                    .order_by(source_table.trade_date.asc())
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                # 无日线数据，跳过
                logger.debug("标的 %s 无日线数据，跳过", ts_code)
                continue

            # 转换为 DataFrame
            records = [{
                "trade_date": r.trade_date,
                "open": float(r.open) if r.open else 0.0,
                "high": float(r.high) if r.high else 0.0,
                "low": float(r.low) if r.low else 0.0,
                "close": float(r.close) if r.close else 0.0,
                "vol": float(r.vol) if r.vol else 0.0,
            } for r in rows]
            df = pd.DataFrame(records)

            # 计算指标
            df_with_indicators = compute_indicators_generic(df)

            # 构建写入行（所有交易日的指标）
            for _, row in df_with_indicators.iterrows():
                batch_rows.append(
                    _build_indicator_row(ts_code, row["trade_date"], row)
                )

            success += 1

        except Exception as e:
            logger.error("计算标的 %s 指标失败: %s", ts_code, e)
            failed += 1

        batch_count += 1

        # 每 BATCH_COMMIT_SIZE 个标的提交一次
        if batch_count >= BATCH_COMMIT_SIZE and batch_rows:
            async with session_factory() as session:
                await _upsert_technical_rows_generic(session, batch_rows, target_table)
                await session.commit()
            logger.info(
                "已提交 %d 个标的的指标数据（%d 行）",
                batch_count, len(batch_rows),
            )
            batch_rows = []
            batch_count = 0

        # 进度回调
        if progress_callback and (i + 1) % 500 == 0:
            progress_callback(i + 1, total)

    # 提交剩余数据
    if batch_rows:
        async with session_factory() as session:
            await _upsert_technical_rows_generic(session, batch_rows, target_table)
            await session.commit()

    elapsed = round(time.time() - start_time, 2)
    summary = {
        "total": total,
        "success": success,
        "failed": failed,
        "elapsed_seconds": elapsed,
    }

    # 记录总体汇总日志
    avg_time = elapsed / total if total > 0 else 0
    logger.info(
        "[技术指标] 全量计算完成（%s → %s）：成功 %d 个，失败 %d 个，总耗时 %.1fs，平均 %.3fs/个",
        source_table.__tablename__, target_table.__tablename__, success, failed, elapsed, avg_time,
    )

    # 检测慢速计算（总耗时 >30 分钟）
    if elapsed > 1800:
        logger.warning("[技术指标] 慢速计算：全量计算耗时 %.1fs (%.1f分钟)", elapsed, elapsed / 60)

    return summary


async def compute_incremental_generic(
    session_factory: async_sessionmaker[AsyncSession],
    source_table: Type[DeclarativeBase],
    target_table: Type[DeclarativeBase],
    target_date: date | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict:
    """泛化增量计算技术指标：仅计算指定交易日（默认最新）的指标。

    对每个标的加载 LOOKBACK_DAYS 天历史数据，计算指标后仅
    UPSERT 目标日期那一行到指定技术指标表。

    Args:
        session_factory: 异步数据库会话工厂
        source_table: 源数据表模型（StockDaily/IndexDaily/ConceptDaily）
        target_table: 目标技术指标表模型（TechnicalDaily/IndexTechnicalDaily/ConceptTechnicalDaily）
        target_date: 目标交易日，None 表示自动检测最新交易日
        progress_callback: 可选的进度回调函数

    Returns:
        汇总字典：{"trade_date": "YYYY-MM-DD", "total": N, "success": M, "failed": F}
    """
    start_time = time.time()

    # 1. 确定目标交易日
    if target_date is None:
        async with session_factory() as session:
            result = await session.execute(
                select(source_table.trade_date)
                .order_by(source_table.trade_date.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                logger.warning("%s 表无数据，无法确定最新交易日", source_table.__tablename__)
                return {"trade_date": None, "total": 0, "success": 0, "failed": 0}
            target_date = row

    logger.info("增量计算目标日期: %s（%s → %s）", target_date,
                source_table.__tablename__, target_table.__tablename__)

    # 2. 查询在目标日期有日线数据的所有标的
    async with session_factory() as session:
        stmt = (
            select(source_table.ts_code)
            .where(source_table.trade_date == target_date)
            .distinct()
        )
        result = await session.execute(stmt)
        target_codes = [row[0] for row in result.all()]

    total = len(target_codes)
    success = 0
    failed = 0
    batch_rows: list[dict] = []
    batch_count = 0

    logger.info("目标日期 %s 共 %d 个标的需要计算", target_date, total)

    for i, ts_code in enumerate(target_codes):
        try:
            # 加载历史数据（截止到目标日期）
            async with session_factory() as session:
                stmt = (
                    select(source_table)
                    .where(
                        source_table.ts_code == ts_code,
                        source_table.trade_date <= target_date,
                    )
                    .order_by(source_table.trade_date.desc())
                    .limit(LOOKBACK_DAYS)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()

            if not rows:
                continue

            # 转换为 DataFrame（注意：查询是 DESC 排序，需要反转）
            records = [{
                "trade_date": r.trade_date,
                "open": float(r.open) if r.open else 0.0,
                "high": float(r.high) if r.high else 0.0,
                "low": float(r.low) if r.low else 0.0,
                "close": float(r.close) if r.close else 0.0,
                "vol": float(r.vol) if r.vol else 0.0,
            } for r in reversed(rows)]
            df = pd.DataFrame(records)

            # 计算指标
            df_with_indicators = compute_indicators_generic(df)

            # 仅取目标日期那一行
            target_row = df_with_indicators[
                df_with_indicators["trade_date"] == target_date
            ]
            if not target_row.empty:
                batch_rows.append(
                    _build_indicator_row(ts_code, target_date, target_row.iloc[0])
                )

            success += 1

        except Exception as e:
            logger.error("增量计算标的 %s 指标失败: %s", ts_code, e)
            failed += 1

        batch_count += 1

        # 每 BATCH_COMMIT_SIZE 个标的提交一次
        if batch_count >= BATCH_COMMIT_SIZE and batch_rows:
            async with session_factory() as session:
                await _upsert_technical_rows_generic(session, batch_rows, target_table)
                await session.commit()
            batch_rows = []
            batch_count = 0

        # 进度回调
        if progress_callback and (i + 1) % 500 == 0:
            progress_callback(i + 1, total)

    # 提交剩余数据
    if batch_rows:
        async with session_factory() as session:
            await _upsert_technical_rows_generic(session, batch_rows, target_table)
            await session.commit()

    elapsed = round(time.time() - start_time, 2)
    summary = {
        "trade_date": str(target_date),
        "total": total,
        "success": success,
        "failed": failed,
        "elapsed_seconds": elapsed,
    }

    # 记录总体汇总日志
    avg_time = elapsed / total if total > 0 else 0
    logger.info(
        "[技术指标] 增量计算完成（%s → %s）：日期 %s，成功 %d 个，失败 %d 个，总耗时 %.1fs，平均 %.3fs/个",
        source_table.__tablename__, target_table.__tablename__, target_date, success, failed, elapsed, avg_time,
    )

    # 检测慢速计算（总耗时 >10 分钟）
    if elapsed > 600:
        logger.warning("[技术指标] 慢速计算：增量计算耗时 %.1fs (%.1f分钟)", elapsed, elapsed / 60)

    return summary
