from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FinanceIndicator(Base):
    __tablename__ = "finance_indicator"
    __table_args__ = (
        Index("idx_finance_code_date", "ts_code", "end_date", postgresql_ops={"end_date": "DESC"}),
        Index("idx_finance_end_date", "end_date"),
        Index("idx_finance_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(8), primary_key=True, default="Q")
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Profitability
    eps: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    roe: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    roe_diluted: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_margin: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    # Growth
    revenue_yoy: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    profit_yoy: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    # Valuation
    pe_ttm: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    pb: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ps_ttm: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)
    circ_mv: Mapped[float | None] = mapped_column(Numeric(20, 2), nullable=True)

    # Solvency
    current_ratio: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    quick_ratio: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    debt_ratio: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    # Cash flow
    ocf_per_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class IncomeStatement(Base):
    """利润表业务表（从 raw_tushare_income ETL 而来）。"""

    __tablename__ = "income_statement"
    __table_args__ = (
        Index("idx_income_code_date", "ts_code", "end_date", postgresql_ops={"end_date": "DESC"}),
        Index("idx_income_end_date", "end_date"),
        Index("idx_income_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(8), primary_key=True, default="1")
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 收入
    total_revenue: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    revenue: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 成本费用
    oper_cost: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cogs: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    sell_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    admin_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fin_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    rd_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 利润
    operate_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    income_tax: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_income_attr_p: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 每股
    basic_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    diluted_eps: Mapped[float | None] = mapped_column(Numeric(12, 4), nullable=True)
    # 其他
    ebit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    ebitda: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    invest_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    non_oper_income: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    non_oper_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class BalanceSheet(Base):
    """资产负债表业务表（从 raw_tushare_balancesheet ETL 而来）。"""

    __tablename__ = "balance_sheet"
    __table_args__ = (
        Index("idx_bs_code_date", "ts_code", "end_date", postgresql_ops={"end_date": "DESC"}),
        Index("idx_bs_end_date", "end_date"),
        Index("idx_bs_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(8), primary_key=True, default="1")
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 资产
    total_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cur_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_nca: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    money_cap: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    accounts_receiv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    notes_receiv: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    prepayment: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    contract_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    inventories: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    fix_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    intan_assets: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    goodwill: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 负债
    total_liab: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_cur_liab: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_ncl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    st_borr: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    lt_borr: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    bond_payable: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    notes_payable: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    adv_receipts: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    contract_liab: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 股东权益
    total_hldr_eqy_exc_min_int: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_hldr_eqy_inc_min_int: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    total_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    cap_rese: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    surplus_rese: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    undistr_porfit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    minority_int: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    treasury_share: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class CashFlowStatement(Base):
    """现金流量表业务表（从 raw_tushare_cashflow ETL 而来）。"""

    __tablename__ = "cash_flow_statement"
    __table_args__ = (
        Index("idx_cf_code_date", "ts_code", "end_date", postgresql_ops={"end_date": "DESC"}),
        Index("idx_cf_end_date", "end_date"),
        Index("idx_cf_ann_date", "ann_date"),
    )

    ts_code: Mapped[str] = mapped_column(String(16), primary_key=True)
    end_date: Mapped[date] = mapped_column(Date, primary_key=True)
    report_type: Mapped[str] = mapped_column(String(8), primary_key=True, default="1")
    ann_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # 三大活动现金流
    n_cashflow_act: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_cashflow_inv_act: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_cash_flows_fnc_act: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 经营活动明细
    c_fr_sale_sg: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_paid_goods_s: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_paid_to_for_empl: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_paid_for_taxes: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 投资活动明细
    c_pay_acq_const_fiolta: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 筹资活动明细
    c_recp_borrow: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_pay_dist_dpcp_int_exp: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 现金余额
    c_cash_equ_end_period: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    c_cash_equ_beg_period: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    n_incr_cash_cash_equ: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    # 间接法
    free_cashflow: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    net_profit: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    depr_fa_coga_dpba: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)
    invest_loss: Mapped[float | None] = mapped_column(Numeric(20, 4), nullable=True)

    data_source: Mapped[str] = mapped_column(String(16), default="tushare")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
