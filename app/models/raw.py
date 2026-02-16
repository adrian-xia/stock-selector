"""Tushare 原始数据表模型。

每个 Tushare 接口对应一张 raw_tushare_* 表，字段与 API 输出一一对应，不做任何转换。
日期字段保持 VARCHAR(8) 的 YYYYMMDD 格式，数值字段使用 NUMERIC。
每张表包含 fetched_at 时间戳，记录数据拉取时间。
"""

from datetime import datetime

from sqlalchemy import DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


# =====================================================================
# P0 核心原始表（6 张）
# =====================================================================


class RawTushareStockBasic(Base):
    """股票基础信息原始表（对应 stock_basic 接口）。"""

    __tablename__ = "raw_tushare_stock_basic"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    symbol: Mapped[str | None] = mapped_column(String(10), nullable=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    area: Mapped[str | None] = mapped_column(String(16), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fullname: Mapped[str | None] = mapped_column(String(64), nullable=True)
    enname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    cnspell: Mapped[str | None] = mapped_column(String(32), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(8), nullable=True)
    curr_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    list_status: Mapped[str | None] = mapped_column(String(4), nullable=True)
    list_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    delist_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_hs: Mapped[str | None] = mapped_column(String(4), nullable=True)
    act_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    act_ent_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
class RawTushareTradeCal(Base):
    """交易日历原始表（对应 trade_cal 接口）。"""

    __tablename__ = "raw_tushare_trade_cal"

    exchange: Mapped[str] = mapped_column(String(8), primary_key=True)
    cal_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    is_open: Mapped[str | None] = mapped_column(String(4), nullable=True)
    pretrade_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDaily(Base):
    """A股日线行情原始表（对应 daily 接口）。"""

    __tablename__ = "raw_tushare_daily"
    __table_args__ = (
        Index("idx_raw_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareAdjFactor(Base):
    """复权因子原始表（对应 adj_factor 接口）。"""

    __tablename__ = "raw_tushare_adj_factor"
    __table_args__ = (
        Index("idx_raw_adj_factor_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    adj_factor: Mapped[float | None] = mapped_column(Numeric(16, 6), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
class RawTushareDailyBasic(Base):
    """每日指标原始表（对应 daily_basic 接口）。

    包含 PE/PB/换手率/市值等基本面指标。
    """

    __tablename__ = "raw_tushare_daily_basic"
    __table_args__ = (
        Index("idx_raw_daily_basic_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate_f: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    volume_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    pe_ttm: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    pb: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    ps: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    ps_ttm: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    dv_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dv_ttm: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    free_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    circ_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkLimit(Base):
    """每日涨跌停价格原始表（对应 stk_limit 接口）。"""

    __tablename__ = "raw_tushare_stk_limit"
    __table_args__ = (
        Index("idx_raw_stk_limit_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    up_limit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    down_limit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# =====================================================================
# P2 资金流向原始表（10 张）
# =====================================================================


class RawTushareMoneyflow(Base):
    """个股资金流向原始表（对应 moneyflow 接口）。"""

    __tablename__ = "raw_tushare_moneyflow"
    __table_args__ = (
        Index("idx_raw_moneyflow_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    # 小单
    buy_sm_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    buy_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_sm_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    sell_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 中单
    buy_md_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    buy_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_md_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    sell_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 大单
    buy_lg_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    buy_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_lg_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    sell_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 特大单
    buy_elg_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    buy_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_elg_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    sell_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 净流入
    net_mf_vol: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    net_mf_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowDc(Base):
    """个股资金流向原始表 - 东方财富（对应 moneyflow_dc 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_dc"
    __table_args__ = (
        Index("idx_raw_moneyflow_dc_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 主力净流入
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 超大单净流入
    buy_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_elg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 大单净流入
    buy_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_lg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 中单净流入
    buy_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_md_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 小单净流入
    buy_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_sm_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowThs(Base):
    """个股资金流向原始表 - 同花顺（对应 moneyflow_ths 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_ths"
    __table_args__ = (
        Index("idx_raw_moneyflow_ths_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    latest: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 资金净流入
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_d5_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 大单净流入
    buy_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_lg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 中单净流入
    buy_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_md_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 小单净流入
    buy_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_sm_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowHsgt(Base):
    """沪深港通资金流向原始表（对应 moneyflow_hsgt 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_hsgt"

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    ggt_ss: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ggt_sz: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    hgt: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sgt: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    north_money: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    south_money: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowIndThs(Base):
    """同花顺行业资金流向原始表（对应 moneyflow_ind_ths 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_ind_ths"
    __table_args__ = (
        Index("idx_raw_moneyflow_ind_ths_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    industry: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_stock: Mapped[str | None] = mapped_column(String(32), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    company_num: Mapped[int | None] = mapped_column(Numeric(10, 0), nullable=True)
    pct_change_stock: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    net_buy_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_sell_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowCntThs(Base):
    """同花顺概念板块资金流向原始表（对应 moneyflow_cnt_ths 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_cnt_ths"
    __table_args__ = (
        Index("idx_raw_moneyflow_cnt_ths_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    lead_stock: Mapped[str | None] = mapped_column(String(32), nullable=True)
    close_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    industry_index: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    company_num: Mapped[int | None] = mapped_column(Numeric(10, 0), nullable=True)
    pct_change_stock: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    net_buy_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_sell_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowIndDc(Base):
    """东财概念及行业板块资金流向原始表（对应 moneyflow_ind_dc 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_ind_dc"
    __table_args__ = (
        Index("idx_raw_moneyflow_ind_dc_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    content_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 主力净流入
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 超大单净流入
    buy_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_elg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 大单净流入
    buy_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_lg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 中单净流入
    buy_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_md_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 小单净流入
    buy_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_sm_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    buy_sm_amount_stock: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rank: Mapped[int | None] = mapped_column(Numeric(10, 0), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMoneyflowMktDc(Base):
    """大盘资金流向原始表 - 东方财富（对应 moneyflow_mkt_dc 接口）。"""

    __tablename__ = "raw_tushare_moneyflow_mkt_dc"

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    close_sh: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_change_sh: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close_sz: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_change_sz: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 主力净流入
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 超大单净流入
    buy_elg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_elg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 大单净流入
    buy_lg_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_lg_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 中单净流入
    buy_md_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_md_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 小单净流入
    buy_sm_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_sm_amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareTopList(Base):
    """龙虎榜每日明细原始表（对应 top_list 接口）。"""

    __tablename__ = "raw_tushare_top_list"
    __table_args__ = (
        Index("idx_raw_top_list_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    l_sell: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    l_buy: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    l_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    amount_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    float_values: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareTopInst(Base):
    """龙虎榜机构明细原始表（对应 top_inst 接口）。"""

    __tablename__ = "raw_tushare_top_inst"
    __table_args__ = (
        Index("idx_raw_top_inst_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    exalter: Mapped[str] = mapped_column(String(128), primary_key=True)
    side: Mapped[str | None] = mapped_column(String(4), nullable=True)
    buy: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    buy_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    sell: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    net_buy: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
