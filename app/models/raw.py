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
