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
# P1 财务数据原始表（10 张）
# =====================================================================


class RawTushareFinaIndicator(Base):
    """财务指标原始表（对应 fina_indicator 接口）。
    
    包含每股指标、偿债能力、营运能力、盈利能力、资本结构、收益率、
    单季度指标、同比增长率等 100+ 个财务指标。
    """

    __tablename__ = "raw_tushare_fina_indicator"
    __table_args__ = (
        Index("idx_raw_fina_indicator_ann_date", "ann_date"),
        Index("idx_raw_fina_indicator_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    # 每股指标
    eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dt_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_revenue_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    revenue_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    capital_rese_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    surplus_rese_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    undist_profit_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    extra_item: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    profit_dedt: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 偿债能力
    gross_margin: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    current_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    quick_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cash_ratio: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 营运能力
    invturn_days: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    arturn_days: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    inv_turn: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ar_turn: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ca_turn: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fa_turn: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    assets_turn: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 盈利能力
    op_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    valuechange_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    interst_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    daa: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ebit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ebitda: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fcff: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fcfe: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 资本结构
    current_exint: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    noncurrent_exint: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    interestdebt: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    netdebt: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    tangible_asset: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    working_capital: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    networking_capital: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    invest_capital: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    retained_earnings: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 更多每股指标
    diluted2_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    bps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocfps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    retainedps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cfps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ebit_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fcff_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fcfe_ps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 盈利能力比率
    netprofit_margin: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    grossprofit_margin: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cogs_of_sales: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    expense_of_sales: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    profit_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    saleexp_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    adminexp_of_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    finaexp_of_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    impai_ttm: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    gc_of_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    op_of_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ebit_of_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 收益率
    roe: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roe_waa: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roe_dt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roa: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    npta: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roic: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roe_yearly: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roa2_yearly: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roe_avg: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 其他指标
    opincome_of_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    investincome_of_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    n_op_profit_of_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    tax_to_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dtprofit_to_profit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    salescash_to_or: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_or: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_opincome: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    capitalized_to_da: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    debt_to_assets: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    assets_to_eqt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dp_assets_to_eqt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ca_to_assets: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    nca_to_assets: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    tbassets_to_totalassets: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    int_to_talcap: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    eqt_to_talcapital: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    currentdebt_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    longdeb_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_shortdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    debt_to_eqt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    eqt_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    eqt_to_interestdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    tangibleasset_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    tangasset_to_intdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    tangibleasset_to_netdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_interestdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_netdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ebit_to_interest: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    longdebt_to_workingcapital: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ebitda_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turn_days: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roa_yearly: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roa_dp: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fixed_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    profit_prefin_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    non_op_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    op_to_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    nop_to_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_to_profit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cash_to_liqdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cash_to_liqdebt_withinterest: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    op_to_liqdebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    op_to_debt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roic_yearly: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_fa_trun: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    profit_to_op: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 单季度指标
    q_opincome: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    q_investincome: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    q_dtprofit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    q_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_netprofit_margin: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_gsprofit_margin: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_exp_to_sales: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_profit_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_saleexp_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_adminexp_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_finaexp_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_impair_to_gr_ttm: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_gc_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_op_to_gr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_roe: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_dt_roe: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_npta: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_opincome_to_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_investincome_to_ebt: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_dtprofit_to_profit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_salescash_to_or: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_ocf_to_sales: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_ocf_to_or: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 同比增长率
    basic_eps_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dt_eps_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cfps_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    op_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ebt_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    netprofit_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    dt_netprofit_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ocf_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    roe_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    bps_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    assets_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    eqt_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    tr_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    or_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_gr_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_gr_qoq: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_sales_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_sales_qoq: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_op_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_op_qoq: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_profit_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_profit_qoq: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_netprofit_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    q_netprofit_qoq: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    equity_yoy: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rd_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIncome(Base):
    """利润表原始表（对应 income 接口）。"""

    __tablename__ = "raw_tushare_income"
    __table_args__ = (
        Index("idx_raw_income_ann_date", "ann_date"),
        Index("idx_raw_income_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    f_ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    comp_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    end_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    basic_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    diluted_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_revenue: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cogs: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    oper_cost: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    admin_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fin_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    operate_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    income_tax: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_income_attr_p: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareBalancesheet(Base):
    """资产负债表原始表（对应 balancesheet 接口）。"""

    __tablename__ = "raw_tushare_balancesheet"
    __table_args__ = (
        Index("idx_raw_balancesheet_ann_date", "ann_date"),
        Index("idx_raw_balancesheet_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    f_ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    comp_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    end_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    cap_rese: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    undistr_porfit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    surplus_rese: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    money_cap: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    accounts_receiv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    inventories: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cur_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fix_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_nca: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cur_liab: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_ncl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_liab: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_hldr_eqy_exc_min_int: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCashflow(Base):
    """现金流量表原始表（对应 cashflow 接口）。"""

    __tablename__ = "raw_tushare_cashflow"
    __table_args__ = (
        Index("idx_raw_cashflow_ann_date", "ann_date"),
        Index("idx_raw_cashflow_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    f_ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    report_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    comp_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    end_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    n_cashflow_act: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_cashflow_inv_act: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_cash_flows_fnc_act: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_cash_equ_end_period: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_cash_equ_beg_period: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_recp_cash_sale_g: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_paid_goods_s: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_paid_to_for_empl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_paid_for_taxes: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDividend(Base):
    """分红送股原始表（对应 dividend 接口）。"""

    __tablename__ = "raw_tushare_dividend"
    __table_args__ = (
        Index("idx_raw_dividend_div_proc", "div_proc"),
        Index("idx_raw_dividend_record_date", "record_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    div_proc: Mapped[str | None] = mapped_column(String(16), nullable=True)
    stk_div: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    stk_bo_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    stk_co_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cash_div: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cash_div_tax: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    record_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ex_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pay_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    div_listdate: Mapped[str | None] = mapped_column(String(8), nullable=True)
    imp_ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    base_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareForecast(Base):
    """业绩预告原始表（对应 forecast 接口）。"""

    __tablename__ = "raw_tushare_forecast"
    __table_args__ = (
        Index("idx_raw_forecast_ann_date", "ann_date"),
        Index("idx_raw_forecast_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    p_change_min: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    p_change_max: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    net_profit_min: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_profit_max: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    last_parent_net: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    first_ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareExpress(Base):
    """业绩快报原始表（对应 express 接口）。"""

    __tablename__ = "raw_tushare_express"
    __table_args__ = (
        Index("idx_raw_express_ann_date", "ann_date"),
        Index("idx_raw_express_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    operate_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_hldr_eqy_exc_min_int: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    diluted_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    diluted_roe: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_net_profit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    bps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_sales: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_op: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_tp: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_dedu_np: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_roe: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    growth_assets: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    yoy_equity: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    growth_bps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    or_last_year: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    op_last_year: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    tp_last_year: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    np_last_year: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    eps_last_year: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    open_net_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    open_bps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    perf_summary: Mapped[str | None] = mapped_column(String(512), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareFinaAudit(Base):
    """财务审计意见原始表（对应 fina_audit 接口）。"""

    __tablename__ = "raw_tushare_fina_audit"
    __table_args__ = (
        Index("idx_raw_fina_audit_ann_date", "ann_date"),
        Index("idx_raw_fina_audit_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    audit_result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_fees: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    audit_agency: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audit_sign: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareFinaMainbz(Base):
    """主营业务构成原始表（对应 fina_mainbz 接口）。"""

    __tablename__ = "raw_tushare_fina_mainbz"
    __table_args__ = (
        Index("idx_raw_fina_mainbz_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    bz_item: Mapped[str] = mapped_column(String(128), primary_key=True)
    bz_sales: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    bz_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    bz_cost: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    curr_type: Mapped[str | None] = mapped_column(String(8), nullable=True)
    update_flag: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDisclosureDate(Base):
    """财报披露计划原始表（对应 disclosure_date 接口）。"""

    __tablename__ = "raw_tushare_disclosure_date"
    __table_args__ = (
        Index("idx_raw_disclosure_date_actual_date", "actual_date"),
        Index("idx_raw_disclosure_date_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    pre_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    actual_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    modify_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
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


# =====================================================================
# P3 指数数据原始表（12 张）
# =====================================================================


class RawTushareIndexBasic(Base):
    """指数基础信息原始表（对应 index_basic 接口）。"""

    __tablename__ = "raw_tushare_index_basic"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fullname: Mapped[str | None] = mapped_column(String(128), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    publisher: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    category: Mapped[str | None] = mapped_column(String(16), nullable=True)
    base_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    base_point: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    list_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    weight_rule: Mapped[str | None] = mapped_column(String(128), nullable=True)
    desc: Mapped[str | None] = mapped_column(String(512), nullable=True)
    exp_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexWeight(Base):
    """指数成分股权重原始表（对应 index_weight 接口）。"""

    __tablename__ = "raw_tushare_index_weight"
    __table_args__ = (
        Index("idx_raw_index_weight_index_code", "index_code"),
        Index("idx_raw_index_weight_trade_date", "trade_date"),
    )

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    con_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    weight: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexDaily(Base):
    """指数日线行情原始表（对应 index_daily 接口）。"""

    __tablename__ = "raw_tushare_index_daily"
    __table_args__ = (
        Index("idx_raw_index_daily_trade_date", "trade_date"),
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
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexWeekly(Base):
    """指数周线行情原始表（对应 index_weekly 接口）。"""

    __tablename__ = "raw_tushare_index_weekly"
    __table_args__ = (
        Index("idx_raw_index_weekly_trade_date", "trade_date"),
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
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexMonthly(Base):
    """指数月线行情原始表（对应 index_monthly 接口）。"""

    __tablename__ = "raw_tushare_index_monthly"
    __table_args__ = (
        Index("idx_raw_index_monthly_trade_date", "trade_date"),
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
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexDailybasic(Base):
    """指数每日指标原始表（对应 index_dailybasic 接口）。"""

    __tablename__ = "raw_tushare_index_dailybasic"
    __table_args__ = (
        Index("idx_raw_index_dailybasic_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    free_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    turnover_rate_f: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    pe_ttm: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    pb: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexGlobal(Base):
    """国际指数行情原始表（对应 index_global 接口）。"""

    __tablename__ = "raw_tushare_index_global"
    __table_args__ = (
        Index("idx_raw_index_global_trade_date", "trade_date"),
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
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDailyInfo(Base):
    """大盘每日指标原始表（对应 daily_info 接口）。"""

    __tablename__ = "raw_tushare_daily_info"

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ts_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    com_count: Mapped[int | None] = mapped_column(Numeric(10, 0), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    trans_count: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    tr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareSzDailyInfo(Base):
    """深圳市场每日指标原始表（对应 sz_daily_info 接口）。"""

    __tablename__ = "raw_tushare_sz_daily_info"

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ts_name: Mapped[str | None] = mapped_column(String(32), nullable=True)
    com_count: Mapped[int | None] = mapped_column(Numeric(10, 0), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_mv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    trans_count: Mapped[int | None] = mapped_column(Numeric(20, 0), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(16, 4), nullable=True)
    tr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexClassify(Base):
    """申万行业分类原始表（对应 index_classify 接口）。"""

    __tablename__ = "raw_tushare_index_classify"

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    industry_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[str | None] = mapped_column(String(4), nullable=True)
    industry_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    src: Mapped[str | None] = mapped_column(String(16), nullable=True)
    parent_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexMemberAll(Base):
    """申万行业成分股原始表（对应 index_member_all 接口）。"""

    __tablename__ = "raw_tushare_index_member_all"
    __table_args__ = (
        Index("idx_raw_index_member_all_index_code", "index_code"),
        Index("idx_raw_index_member_all_in_date", "in_date"),
    )

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    con_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    in_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    out_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_new: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareSwDaily(Base):
    """申万行业日线行情原始表（对应 sw_daily 接口）。"""

    __tablename__ = "raw_tushare_sw_daily"
    __table_args__ = (
        Index("idx_raw_sw_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCiIndexMember(Base):
    """中信行业成分股原始表（对应 ci_index_member 接口）。"""

    __tablename__ = "raw_tushare_ci_index_member"
    __table_args__ = (
        Index("idx_raw_ci_index_member_index_code", "index_code"),
        Index("idx_raw_ci_index_member_in_date", "in_date"),
    )

    index_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    con_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    in_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    out_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_new: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCiDaily(Base):
    """中信行业日线行情原始表（对应 ci_daily 接口）。"""

    __tablename__ = "raw_tushare_ci_daily"
    __table_args__ = (
        Index("idx_raw_ci_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareIndexFactorPro(Base):
    """指数技术面因子原始表（对应 index_factor_pro 接口）。"""

    __tablename__ = "raw_tushare_index_factor_pro"
    __table_args__ = (
        Index("idx_raw_index_factor_pro_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    # 均线指标
    ma5: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma10: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma20: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma60: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma120: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    ma250: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # MACD 指标
    macd_dif: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # KDJ 指标
    kdj_k: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # RSI 指标
    rsi6: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi12: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi24: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 布林带指标
    boll_upper: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_lower: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 其他指标
    atr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cci: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    wr: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareTdxDaily(Base):
    """通达信日线行情原始表（对应 tdx_daily 接口）。"""

    __tablename__ = "raw_tushare_tdx_daily"
    __table_args__ = (
        Index("idx_raw_tdx_daily_trade_date", "trade_date"),
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
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# =====================================================================
# P4 板块数据原始表（8 张）
# =====================================================================


class RawTushareThsIndex(Base):
    """同花顺板块指数原始表（对应 ths_index 接口）。"""

    __tablename__ = "raw_tushare_ths_index"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    count: Mapped[int | None] = mapped_column(nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)
    list_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareThsDaily(Base):
    """同花顺板块日线行情原始表（对应 ths_daily 接口）。"""

    __tablename__ = "raw_tushare_ths_daily"
    __table_args__ = (
        Index("idx_raw_ths_daily_code_date", "ts_code", "trade_date"),
        Index("idx_raw_ths_daily_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    open: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareThsMember(Base):
    """同花顺板块成分股原始表（对应 ths_member 接口）。"""

    __tablename__ = "raw_tushare_ths_member"
    __table_args__ = (
        Index("idx_raw_ths_member_ts_code", "ts_code"),
        Index("idx_raw_ths_member_code", "code"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    weight: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    in_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    out_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_new: Mapped[str | None] = mapped_column(String(1), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDcIndex(Base):
    """东方财富板块指数原始表（对应 dc_index 接口）。"""

    __tablename__ = "raw_tushare_dc_index"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    src: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDcMember(Base):
    """东方财富板块成分股原始表（对应 dc_member 接口）。"""

    __tablename__ = "raw_tushare_dc_member"
    __table_args__ = (
        Index("idx_raw_dc_member_ts_code", "ts_code"),
        Index("idx_raw_dc_member_code", "code"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    in_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    out_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDcHotNew(Base):
    """东方财富热门板块原始表（对应 dc_hot_new 接口）。"""

    __tablename__ = "raw_tushare_dc_hot_new"
    __table_args__ = (
        Index("idx_raw_dc_hot_new_ts_code", "ts_code"),
        Index("idx_raw_dc_hot_new_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareTdxIndex(Base):
    """通达信板块指数原始表（对应 tdx_index 接口）。"""

    __tablename__ = "raw_tushare_tdx_index"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    market: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareTdxMember(Base):
    """通达信板块成分股原始表（对应 tdx_member 接口）。"""

    __tablename__ = "raw_tushare_tdx_member"
    __table_args__ = (
        Index("idx_raw_tdx_member_ts_code", "ts_code"),
        Index("idx_raw_tdx_member_code", "code"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# =====================================================================
# P5 扩展数据原始表（48 张）
# =====================================================================

# 11a. 基础数据补充（7 张）


class RawTushareNamechange(Base):
    """股票曾用名原始表（对应 namechange 接口）。"""

    __tablename__ = "raw_tushare_namechange"
    __table_args__ = (
        Index("idx_raw_namechange_ts_code", "ts_code"),
        Index("idx_raw_namechange_start_date", "start_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    start_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStockCompany(Base):
    """上市公司基本信息原始表（对应 stock_company 接口）。"""

    __tablename__ = "raw_tushare_stock_company"

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    exchange: Mapped[str | None] = mapped_column(String(16), nullable=True)
    chairman: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manager: Mapped[str | None] = mapped_column(String(64), nullable=True)
    secretary: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reg_capital: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    setup_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    province: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(32), nullable=True)
    introduction: Mapped[str | None] = mapped_column(nullable=True)
    website: Mapped[str | None] = mapped_column(String(128), nullable=True)
    email: Mapped[str | None] = mapped_column(String(64), nullable=True)
    office: Mapped[str | None] = mapped_column(String(256), nullable=True)
    employees: Mapped[int | None] = mapped_column(nullable=True)
    main_business: Mapped[str | None] = mapped_column(nullable=True)
    business_scope: Mapped[str | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkManagers(Base):
    """上市公司管理层原始表（对应 stk_managers 接口）。"""

    __tablename__ = "raw_tushare_stk_managers"
    __table_args__ = (
        Index("idx_raw_stk_managers_ts_code", "ts_code"),
        Index("idx_raw_stk_managers_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    gender: Mapped[str | None] = mapped_column(String(8), nullable=True)
    lev: Mapped[str | None] = mapped_column(String(32), nullable=True)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    edu: Mapped[str | None] = mapped_column(String(32), nullable=True)
    national: Mapped[str | None] = mapped_column(String(16), nullable=True)
    birthday: Mapped[str | None] = mapped_column(String(8), nullable=True)
    begin_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    resume: Mapped[str | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkRewards(Base):
    """管理层薪酬和持股原始表（对应 stk_rewards 接口）。"""

    __tablename__ = "raw_tushare_stk_rewards"
    __table_args__ = (
        Index("idx_raw_stk_rewards_ts_code", "ts_code"),
        Index("idx_raw_stk_rewards_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reward: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    hold_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareNewShare(Base):
    """IPO 新股列表原始表（对应 new_share 接口）。"""

    __tablename__ = "raw_tushare_new_share"
    __table_args__ = (Index("idx_raw_new_share_ipo_date", "ipo_date"),)

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    sub_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ipo_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    issue_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    market_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pe: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    limit_amount: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    funds: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ballot: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDailyShare(Base):
    """每日股本变动原始表（对应 daily_share 接口）。"""

    __tablename__ = "raw_tushare_daily_share"
    __table_args__ = (
        Index("idx_raw_daily_share_code_date", "ts_code", "trade_date"),
        Index("idx_raw_daily_share_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    free_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    circ_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkListHis(Base):
    """股票上市历史原始表（对应 stk_list_his 接口）。"""

    __tablename__ = "raw_tushare_stk_list_his"
    __table_args__ = (
        Index("idx_raw_stk_list_his_ts_code", "ts_code"),
        Index("idx_raw_stk_list_his_list_date", "list_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    list_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    delist_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    list_status: Mapped[str | None] = mapped_column(String(1), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# 11b. 行情补充（5 张）


class RawTushareWeekly(Base):
    """周线行情原始表（对应 weekly 接口）。"""

    __tablename__ = "raw_tushare_weekly"
    __table_args__ = (
        Index("idx_raw_weekly_code_date", "ts_code", "trade_date"),
        Index("idx_raw_weekly_trade_date", "trade_date"),
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
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMonthly(Base):
    """月线行情原始表（对应 monthly 接口）。"""

    __tablename__ = "raw_tushare_monthly"
    __table_args__ = (
        Index("idx_raw_monthly_code_date", "ts_code", "trade_date"),
        Index("idx_raw_monthly_trade_date", "trade_date"),
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
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareSuspendD(Base):
    """停复牌信息原始表（对应 suspend_d 接口）。"""

    __tablename__ = "raw_tushare_suspend_d"
    __table_args__ = (
        Index("idx_raw_suspend_d_ts_code", "ts_code"),
        Index("idx_raw_suspend_d_suspend_date", "suspend_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    suspend_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    resume_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    ann_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    suspend_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    reason_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareHsgtTop10(Base):
    """沪深港通十大成交股原始表（对应 hsgt_top10 接口）。"""

    __tablename__ = "raw_tushare_hsgt_top10"
    __table_args__ = (
        Index("idx_raw_hsgt_top10_trade_date", "trade_date"),
        Index("idx_raw_hsgt_top10_ts_code", "ts_code"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    market_type: Mapped[str] = mapped_column(String(8), primary_key=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    net_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    buy: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    sell: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareGgtDaily(Base):
    """港股通每日成交统计原始表（对应 ggt_daily 接口）。"""

    __tablename__ = "raw_tushare_ggt_daily"
    __table_args__ = (Index("idx_raw_ggt_daily_trade_date", "trade_date"),)

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    buy_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    buy_volume: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    sell_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    sell_volume: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# 11c. 市场参考数据（9 张）


class RawTushareTop10Holders(Base):
    """前十大股东原始表（对应 top10_holders 接口）。"""

    __tablename__ = "raw_tushare_top10_holders"
    __table_args__ = (
        Index("idx_raw_top10_holders_ts_code", "ts_code"),
        Index("idx_raw_top10_holders_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    holder_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    hold_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    hold_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareTop10Floatholders(Base):
    """前十大流通股东原始表（对应 top10_floatholders 接口）。"""

    __tablename__ = "raw_tushare_top10_floatholders"
    __table_args__ = (
        Index("idx_raw_top10_floatholders_ts_code", "ts_code"),
        Index("idx_raw_top10_floatholders_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    holder_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    hold_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    hold_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTusharePledgeStat(Base):
    """股权质押统计原始表（对应 pledge_stat 接口）。"""

    __tablename__ = "raw_tushare_pledge_stat"
    __table_args__ = (
        Index("idx_raw_pledge_stat_ts_code", "ts_code"),
        Index("idx_raw_pledge_stat_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    pledge_count: Mapped[int | None] = mapped_column(nullable=True)
    unrest_pledge: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rest_pledge: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    pledge_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTusharePledgeDetail(Base):
    """股权质押明细原始表（对应 pledge_detail 接口）。"""

    __tablename__ = "raw_tushare_pledge_detail"
    __table_args__ = (
        Index("idx_raw_pledge_detail_ts_code", "ts_code"),
        Index("idx_raw_pledge_detail_pledge_date", "pledge_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    holder_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    pledge_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    pledge_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    start_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    end_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    pledgor: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareRepurchase(Base):
    """股票回购原始表（对应 repurchase 接口）。"""

    __tablename__ = "raw_tushare_repurchase"
    __table_args__ = (
        Index("idx_raw_repurchase_ts_code", "ts_code"),
        Index("idx_raw_repurchase_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    proc: Mapped[str | None] = mapped_column(String(32), nullable=True)
    exp_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    high_limit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low_limit: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareShareFloat(Base):
    """限售股解禁原始表（对应 share_float 接口）。"""

    __tablename__ = "raw_tushare_share_float"
    __table_args__ = (
        Index("idx_raw_share_float_ts_code", "ts_code"),
        Index("idx_raw_share_float_float_date", "float_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    float_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    float_share: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    float_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    holder_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    share_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareBlockTrade(Base):
    """大宗交易原始表（对应 block_trade 接口）。"""

    __tablename__ = "raw_tushare_block_trade"
    __table_args__ = (
        Index("idx_raw_block_trade_ts_code", "ts_code"),
        Index("idx_raw_block_trade_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    price: Mapped[float] = mapped_column(Numeric(12, 4), primary_key=True)
    vol: Mapped[float] = mapped_column(Numeric(20, 2), primary_key=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    buyer: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seller: Mapped[str | None] = mapped_column(String(128), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkHoldernumber(Base):
    """股东人数原始表（对应 stk_holdernumber 接口）。"""

    __tablename__ = "raw_tushare_stk_holdernumber"
    __table_args__ = (
        Index("idx_raw_stk_holdernumber_ts_code", "ts_code"),
        Index("idx_raw_stk_holdernumber_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    holder_num: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkHoldertrade(Base):
    """股东增减持原始表（对应 stk_holdertrade 接口）。"""

    __tablename__ = "raw_tushare_stk_holdertrade"
    __table_args__ = (
        Index("idx_raw_stk_holdertrade_ts_code", "ts_code"),
        Index("idx_raw_stk_holdertrade_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    ann_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    holder_name: Mapped[str] = mapped_column(String(128), primary_key=True)
    holder_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    in_de: Mapped[str | None] = mapped_column(String(8), nullable=True)
    change_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    change_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    after_share: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    after_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    avg_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    begin_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    close_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# 11d. 特色数据（9 张）


class RawTushareReportRc(Base):
    """券商月度金股原始表（对应 report_rc 接口）。"""

    __tablename__ = "raw_tushare_report_rc"
    __table_args__ = (
        Index("idx_raw_report_rc_ts_code", "ts_code"),
        Index("idx_raw_report_rc_date", "date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[str] = mapped_column(String(8), primary_key=True)
    broker: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    author: Mapped[str | None] = mapped_column(String(64), nullable=True)
    report_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCyqPerf(Base):
    """筹码分布原始表（对应 cyq_perf 接口）。"""

    __tablename__ = "raw_tushare_cyq_perf"
    __table_args__ = (
        Index("idx_raw_cyq_perf_ts_code", "ts_code"),
        Index("idx_raw_cyq_perf_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    his_low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    his_high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_5pct: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_15pct: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_50pct: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_85pct: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    cost_95pct: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    weight_avg: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    winner_rate: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCyqChips(Base):
    """筹码集中度原始表（对应 cyq_chips 接口）。"""

    __tablename__ = "raw_tushare_cyq_chips"
    __table_args__ = (
        Index("idx_raw_cyq_chips_ts_code", "ts_code"),
        Index("idx_raw_cyq_chips_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    chip_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    chip_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    chip_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkFactor(Base):
    """技术因子（日频）原始表（对应 stk_factor 接口）。"""

    __tablename__ = "raw_tushare_stk_factor"
    __table_args__ = (
        Index("idx_raw_stk_factor_ts_code", "ts_code"),
        Index("idx_raw_stk_factor_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    high: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    low: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    change: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkFactorPro(Base):
    """技术因子（日频增强版）原始表（对应 stk_factor_pro 接口）。"""

    __tablename__ = "raw_tushare_stk_factor_pro"
    __table_args__ = (
        Index("idx_raw_stk_factor_pro_ts_code", "ts_code"),
        Index("idx_raw_stk_factor_pro_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    # 技术指标
    macd_dif: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd_dea: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    macd: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_k: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_d: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    kdj_j: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi_6: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi_12: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    rsi_24: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_upper: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_mid: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    boll_lower: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCcassHold(Base):
    """港股通持股汇总原始表（对应 ccass_hold 接口）。"""

    __tablename__ = "raw_tushare_ccass_hold"
    __table_args__ = (
        Index("idx_raw_ccass_hold_ts_code", "ts_code"),
        Index("idx_raw_ccass_hold_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    hk_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    col_participant: Mapped[int | None] = mapped_column(nullable=True)
    col_holding: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    col_percent: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareCcassHoldDetail(Base):
    """港股通持股明细原始表（对应 ccass_hold_detail 接口）。"""

    __tablename__ = "raw_tushare_ccass_hold_detail"
    __table_args__ = (
        Index("idx_raw_ccass_hold_detail_ts_code", "ts_code"),
        Index("idx_raw_ccass_hold_detail_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    participant_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    participant_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    shareholding: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    shareholding_percent: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareHkHold(Base):
    """沪深港通持股明细原始表（对应 hk_hold 接口）。"""

    __tablename__ = "raw_tushare_hk_hold"
    __table_args__ = (
        Index("idx_raw_hk_hold_ts_code", "ts_code"),
        Index("idx_raw_hk_hold_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    exchange: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkSurv(Base):
    """股票调查问卷原始表（对应 stk_surv 接口）。"""

    __tablename__ = "raw_tushare_stk_surv"
    __table_args__ = (
        Index("idx_raw_stk_surv_ts_code", "ts_code"),
        Index("idx_raw_stk_surv_end_date", "end_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    survey_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    survey_org: Mapped[str | None] = mapped_column(String(128), nullable=True)
    survey_person: Mapped[str | None] = mapped_column(String(64), nullable=True)
    survey_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# 11e. 两融数据（4 张）


class RawTushareMargin(Base):
    """融资融券交易汇总原始表（对应 margin 接口）。"""

    __tablename__ = "raw_tushare_margin"
    __table_args__ = (Index("idx_raw_margin_trade_date", "trade_date"),)

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    exchange_id: Mapped[str] = mapped_column(String(8), primary_key=True)
    rzye: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rzmre: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rzche: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqye: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqmcl: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqchl: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rzrqye: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMarginDetail(Base):
    """融资融券交易明细原始表（对应 margin_detail 接口）。"""

    __tablename__ = "raw_tushare_margin_detail"
    __table_args__ = (
        Index("idx_raw_margin_detail_ts_code", "ts_code"),
        Index("idx_raw_margin_detail_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rzye: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rzmre: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rzche: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqye: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqyl: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqmcl: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rqchl: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    rzrqye: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareMarginTarget(Base):
    """融资融券标的原始表（对应 margin_target 接口）。"""

    __tablename__ = "raw_tushare_margin_target"
    __table_args__ = (Index("idx_raw_margin_target_ts_code", "ts_code"),)

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    in_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    out_date: Mapped[str | None] = mapped_column(String(8), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareSlbLen(Base):
    """转融通借入原始表（对应 slb_len 接口）。"""

    __tablename__ = "raw_tushare_slb_len"
    __table_args__ = (
        Index("idx_raw_slb_len_ts_code", "ts_code"),
        Index("idx_raw_slb_len_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    slb_amt: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    slb_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    slb_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


# 11f. 打板专题（14 张）


class RawTushareLimitListD(Base):
    """每日涨跌停统计原始表（对应 limit_list_d 接口）。"""

    __tablename__ = "raw_tushare_limit_list_d"
    __table_args__ = (
        Index("idx_raw_limit_list_d_ts_code", "ts_code"),
        Index("idx_raw_limit_list_d_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    amp: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fc_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fl_ratio: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    fd_amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    first_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    open_times: Mapped[int | None] = mapped_column(nullable=True)
    up_stat: Mapped[str | None] = mapped_column(String(4), nullable=True)
    limit_times: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareThsLimit(Base):
    """同花顺涨跌停原始表（对应 ths_limit 接口）。"""

    __tablename__ = "raw_tushare_ths_limit"
    __table_args__ = (
        Index("idx_raw_ths_limit_ts_code", "ts_code"),
        Index("idx_raw_ths_limit_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    limit_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    first_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    last_time: Mapped[str | None] = mapped_column(String(8), nullable=True)
    open_times: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareLimitStep(Base):
    """涨跌停阶梯原始表（对应 limit_step 接口）。"""

    __tablename__ = "raw_tushare_limit_step"
    __table_args__ = (
        Index("idx_raw_limit_step_ts_code", "ts_code"),
        Index("idx_raw_limit_step_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    step: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareHmBoard(Base):
    """热门板块原始表（对应 hm_board 接口）。"""

    __tablename__ = "raw_tushare_hm_board"
    __table_args__ = (Index("idx_raw_hm_board_trade_date", "trade_date"),)

    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    board_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    board_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareHmList(Base):
    """热门股票原始表（对应 hm_list 接口）。"""

    __tablename__ = "raw_tushare_hm_list"
    __table_args__ = (
        Index("idx_raw_hm_list_ts_code", "ts_code"),
        Index("idx_raw_hm_list_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    rank: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareHmDetail(Base):
    """热门股票明细原始表（对应 hm_detail 接口）。"""

    __tablename__ = "raw_tushare_hm_detail"
    __table_args__ = (
        Index("idx_raw_hm_detail_ts_code", "ts_code"),
        Index("idx_raw_hm_detail_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkAuction(Base):
    """集合竞价原始表（对应 stk_auction 接口）。"""

    __tablename__ = "raw_tushare_stk_auction"
    __table_args__ = (
        Index("idx_raw_stk_auction_ts_code", "ts_code"),
        Index("idx_raw_stk_auction_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareStkAuctionO(Base):
    """集合竞价（开盘）原始表（对应 stk_auction_o 接口）。"""

    __tablename__ = "raw_tushare_stk_auction_o"
    __table_args__ = (
        Index("idx_raw_stk_auction_o_ts_code", "ts_code"),
        Index("idx_raw_stk_auction_o_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    open: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pre_close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareKplList(Base):
    """科创板涨跌停原始表（对应 kpl_list 接口）。"""

    __tablename__ = "raw_tushare_kpl_list"
    __table_args__ = (
        Index("idx_raw_kpl_list_ts_code", "ts_code"),
        Index("idx_raw_kpl_list_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    limit_type: Mapped[str | None] = mapped_column(String(4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareKplConcept(Base):
    """科创板概念原始表（对应 kpl_concept 接口）。"""

    __tablename__ = "raw_tushare_kpl_concept"
    __table_args__ = (
        Index("idx_raw_kpl_concept_ts_code", "ts_code"),
        Index("idx_raw_kpl_concept_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    concept_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    concept_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareBrokerRecommend(Base):
    """券商推荐原始表（对应 broker_recommend 接口）。"""

    __tablename__ = "raw_tushare_broker_recommend"
    __table_args__ = (
        Index("idx_raw_broker_recommend_ts_code", "ts_code"),
        Index("idx_raw_broker_recommend_date", "date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    date: Mapped[str] = mapped_column(String(8), primary_key=True)
    broker: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rating: Mapped[str | None] = mapped_column(String(16), nullable=True)
    target_price: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareThsHot(Base):
    """同花顺热榜原始表（对应 ths_hot 接口）。"""

    __tablename__ = "raw_tushare_ths_hot"
    __table_args__ = (
        Index("idx_raw_ths_hot_ts_code", "ts_code"),
        Index("idx_raw_ths_hot_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    hot_rank: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareDcHot(Base):
    """东财热榜原始表（对应 dc_hot 接口）。"""

    __tablename__ = "raw_tushare_dc_hot"
    __table_args__ = (
        Index("idx_raw_dc_hot_ts_code", "ts_code"),
        Index("idx_raw_dc_hot_trade_date", "trade_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    trade_date: Mapped[str] = mapped_column(String(8), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    close: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    pct_chg: Mapped[float | None] = mapped_column(Numeric(10, 4), nullable=True)
    hot_rank: Mapped[int | None] = mapped_column(nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )


class RawTushareGgtMonthly(Base):
    """港股通月度统计原始表（对应 ggt_monthly 接口）。"""

    __tablename__ = "raw_tushare_ggt_monthly"
    __table_args__ = (Index("idx_raw_ggt_monthly_month", "month"),)

    month: Mapped[str] = mapped_column(String(8), primary_key=True)
    day_buy_amt: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    day_buy_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    day_sell_amt: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    day_sell_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_buy_amt: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_buy_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_sell_amt: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    total_sell_vol: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
