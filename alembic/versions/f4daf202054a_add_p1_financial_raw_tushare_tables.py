"""add P1 financial raw tushare tables

Revision ID: f4daf202054a
Revises: 7a0c7d9f66b5
Create Date: 2026-02-16 12:24:44.145772

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f4daf202054a'
down_revision: Union[str, Sequence[str], None] = '7a0c7d9f66b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. raw_tushare_fina_indicator - 财务指标原始表
    op.create_table('raw_tushare_fina_indicator',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    # 每股指标
    sa.Column('eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('dt_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('total_revenue_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('revenue_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('capital_rese_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('surplus_rese_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('undist_profit_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('extra_item', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('profit_dedt', sa.Numeric(precision=20, scale=4), nullable=True),
    # 偿债能力
    sa.Column('gross_margin', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('current_ratio', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('quick_ratio', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cash_ratio', sa.Numeric(precision=12, scale=4), nullable=True),
    # 营运能力
    sa.Column('invturn_days', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('arturn_days', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('inv_turn', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ar_turn', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ca_turn', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fa_turn', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('assets_turn', sa.Numeric(precision=12, scale=4), nullable=True),
    # 盈利能力
    sa.Column('op_income', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('valuechange_income', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('interst_income', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('daa', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('ebit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('ebitda', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fcff', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fcfe', sa.Numeric(precision=20, scale=4), nullable=True),
    # 资本结构
    sa.Column('current_exint', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('noncurrent_exint', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('interestdebt', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('netdebt', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('tangible_asset', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('working_capital', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('networking_capital', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('invest_capital', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('retained_earnings', sa.Numeric(precision=20, scale=4), nullable=True),
    # 更多每股指标
    sa.Column('diluted2_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('bps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocfps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('retainedps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cfps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ebit_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fcff_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fcfe_ps', sa.Numeric(precision=12, scale=4), nullable=True),
    # 盈利能力比率
    sa.Column('netprofit_margin', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('grossprofit_margin', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cogs_of_sales', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('expense_of_sales', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('profit_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('saleexp_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('adminexp_of_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('finaexp_of_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('impai_ttm', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('gc_of_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('op_of_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ebit_of_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    # 收益率
    sa.Column('roe', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roe_waa', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roe_dt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roa', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('npta', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roic', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roe_yearly', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roa2_yearly', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roe_avg', sa.Numeric(precision=12, scale=4), nullable=True),
    # 其他指标
    sa.Column('opincome_of_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('investincome_of_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('n_op_profit_of_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('tax_to_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('dtprofit_to_profit', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('salescash_to_or', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_or', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_opincome', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('capitalized_to_da', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('debt_to_assets', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('assets_to_eqt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('dp_assets_to_eqt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ca_to_assets', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('nca_to_assets', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('tbassets_to_totalassets', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('int_to_talcap', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('eqt_to_talcapital', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('currentdebt_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('longdeb_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_shortdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('debt_to_eqt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('eqt_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('eqt_to_interestdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('tangibleasset_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('tangasset_to_intdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('tangibleasset_to_netdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_interestdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_netdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ebit_to_interest', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('longdebt_to_workingcapital', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ebitda_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('turn_days', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roa_yearly', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roa_dp', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('fixed_assets', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('profit_prefin_exp', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('non_op_profit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('op_to_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('nop_to_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_to_profit', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cash_to_liqdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cash_to_liqdebt_withinterest', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('op_to_liqdebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('op_to_debt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roic_yearly', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('total_fa_trun', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('profit_to_op', sa.Numeric(precision=12, scale=4), nullable=True),
    # 单季度指标
    sa.Column('q_opincome', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('q_investincome', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('q_dtprofit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('q_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_netprofit_margin', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_gsprofit_margin', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_exp_to_sales', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_profit_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_saleexp_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_adminexp_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_finaexp_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_impair_to_gr_ttm', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_gc_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_op_to_gr', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_roe', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_dt_roe', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_npta', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_opincome_to_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_investincome_to_ebt', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_dtprofit_to_profit', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_salescash_to_or', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_ocf_to_sales', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_ocf_to_or', sa.Numeric(precision=12, scale=4), nullable=True),
    # 同比增长率
    sa.Column('basic_eps_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('dt_eps_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cfps_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('op_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ebt_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('netprofit_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('dt_netprofit_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('ocf_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('roe_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('bps_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('assets_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('eqt_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('tr_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('or_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_gr_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_gr_qoq', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_sales_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_sales_qoq', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_op_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_op_qoq', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_profit_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_profit_qoq', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_netprofit_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('q_netprofit_qoq', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('equity_yoy', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('rd_exp', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('update_flag', sa.String(length=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_fina_indicator_ann_date', 'raw_tushare_fina_indicator', ['ann_date'], unique=False)
    op.create_index('idx_raw_fina_indicator_end_date', 'raw_tushare_fina_indicator', ['end_date'], unique=False)

    # 2. raw_tushare_income - 利润表原始表
    op.create_table('raw_tushare_income',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('f_ann_date', sa.String(length=8), nullable=True),
    sa.Column('report_type', sa.String(length=8), nullable=True),
    sa.Column('comp_type', sa.String(length=4), nullable=True),
    sa.Column('end_type', sa.String(length=8), nullable=True),
    sa.Column('basic_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('diluted_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('total_revenue', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('revenue', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_cogs', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('oper_cost', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('sell_exp', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('admin_exp', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fin_exp', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('operate_profit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_profit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('income_tax', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('n_income', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('n_income_attr_p', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('update_flag', sa.String(length=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_income_ann_date', 'raw_tushare_income', ['ann_date'], unique=False)
    op.create_index('idx_raw_income_end_date', 'raw_tushare_income', ['end_date'], unique=False)

    # 3. raw_tushare_balancesheet - 资产负债表原始表
    op.create_table('raw_tushare_balancesheet',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('f_ann_date', sa.String(length=8), nullable=True),
    sa.Column('report_type', sa.String(length=8), nullable=True),
    sa.Column('comp_type', sa.String(length=4), nullable=True),
    sa.Column('end_type', sa.String(length=8), nullable=True),
    sa.Column('total_share', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('cap_rese', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('undistr_porfit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('surplus_rese', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('money_cap', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('accounts_receiv', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('inventories', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_cur_assets', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fix_assets', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_nca', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_assets', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_cur_liab', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_ncl', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_liab', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_hldr_eqy_exc_min_int', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('update_flag', sa.String(length=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_balancesheet_ann_date', 'raw_tushare_balancesheet', ['ann_date'], unique=False)
    op.create_index('idx_raw_balancesheet_end_date', 'raw_tushare_balancesheet', ['end_date'], unique=False)

    # 4. raw_tushare_cashflow - 现金流量表原始表
    op.create_table('raw_tushare_cashflow',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('f_ann_date', sa.String(length=8), nullable=True),
    sa.Column('report_type', sa.String(length=8), nullable=True),
    sa.Column('comp_type', sa.String(length=4), nullable=True),
    sa.Column('end_type', sa.String(length=8), nullable=True),
    sa.Column('n_cashflow_act', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('n_cashflow_inv_act', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('n_cash_flows_fnc_act', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('c_cash_equ_end_period', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('c_cash_equ_beg_period', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('c_recp_cash_sale_g', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('c_paid_goods_s', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('c_paid_to_for_empl', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('c_paid_for_taxes', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('update_flag', sa.String(length=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_cashflow_ann_date', 'raw_tushare_cashflow', ['ann_date'], unique=False)
    op.create_index('idx_raw_cashflow_end_date', 'raw_tushare_cashflow', ['end_date'], unique=False)

    # 5. raw_tushare_dividend - 分红送股原始表
    op.create_table('raw_tushare_dividend',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('div_proc', sa.String(length=16), nullable=True),
    sa.Column('stk_div', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('stk_bo_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('stk_co_rate', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cash_div', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('cash_div_tax', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('record_date', sa.String(length=8), nullable=True),
    sa.Column('ex_date', sa.String(length=8), nullable=True),
    sa.Column('pay_date', sa.String(length=8), nullable=True),
    sa.Column('div_listdate', sa.String(length=8), nullable=True),
    sa.Column('imp_ann_date', sa.String(length=8), nullable=True),
    sa.Column('base_share', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'end_date', 'ann_date')
    )
    op.create_index('idx_raw_dividend_div_proc', 'raw_tushare_dividend', ['div_proc'], unique=False)
    op.create_index('idx_raw_dividend_record_date', 'raw_tushare_dividend', ['record_date'], unique=False)

    # 6. raw_tushare_forecast - 业绩预告原始表
    op.create_table('raw_tushare_forecast',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('type', sa.String(length=16), nullable=True),
    sa.Column('p_change_min', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('p_change_max', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('net_profit_min', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('net_profit_max', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('last_parent_net', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('first_ann_date', sa.String(length=8), nullable=True),
    sa.Column('summary', sa.String(length=512), nullable=True),
    sa.Column('change_reason', sa.String(length=512), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_forecast_ann_date', 'raw_tushare_forecast', ['ann_date'], unique=False)
    op.create_index('idx_raw_forecast_end_date', 'raw_tushare_forecast', ['end_date'], unique=False)

    # 7. raw_tushare_express - 业绩快报原始表
    op.create_table('raw_tushare_express',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('revenue', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('operate_profit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_profit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('n_income', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_assets', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('total_hldr_eqy_exc_min_int', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('diluted_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('diluted_roe', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_net_profit', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('bps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_sales', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_op', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_tp', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_dedu_np', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_eps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_roe', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('growth_assets', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('yoy_equity', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('growth_bps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('or_last_year', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('op_last_year', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('tp_last_year', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('np_last_year', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('eps_last_year', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('open_net_assets', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('open_bps', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('perf_summary', sa.String(length=512), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_express_ann_date', 'raw_tushare_express', ['ann_date'], unique=False)
    op.create_index('idx_raw_express_end_date', 'raw_tushare_express', ['end_date'], unique=False)

    # 8. raw_tushare_fina_audit - 财务审计意见原始表
    op.create_table('raw_tushare_fina_audit',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('ann_date', sa.String(length=8), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('audit_result', sa.String(length=64), nullable=True),
    sa.Column('audit_fees', sa.Numeric(precision=12, scale=4), nullable=True),
    sa.Column('audit_agency', sa.String(length=128), nullable=True),
    sa.Column('audit_sign', sa.String(length=128), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'ann_date', 'end_date')
    )
    op.create_index('idx_raw_fina_audit_ann_date', 'raw_tushare_fina_audit', ['ann_date'], unique=False)
    op.create_index('idx_raw_fina_audit_end_date', 'raw_tushare_fina_audit', ['end_date'], unique=False)

    # 9. raw_tushare_fina_mainbz - 主营业务构成原始表
    op.create_table('raw_tushare_fina_mainbz',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('bz_item', sa.String(length=128), nullable=False),
    sa.Column('bz_sales', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('bz_profit', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('bz_cost', sa.Numeric(precision=20, scale=4), nullable=True),
    sa.Column('curr_type', sa.String(length=8), nullable=True),
    sa.Column('update_flag', sa.String(length=4), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'end_date', 'bz_item')
    )
    op.create_index('idx_raw_fina_mainbz_end_date', 'raw_tushare_fina_mainbz', ['end_date'], unique=False)

    # 10. raw_tushare_disclosure_date - 财报披露计划原始表
    op.create_table('raw_tushare_disclosure_date',
    sa.Column('ts_code', sa.String(length=16), nullable=False),
    sa.Column('end_date', sa.String(length=8), nullable=False),
    sa.Column('pre_date', sa.String(length=8), nullable=True),
    sa.Column('actual_date', sa.String(length=8), nullable=True),
    sa.Column('modify_date', sa.String(length=8), nullable=True),
    sa.Column('fetched_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('ts_code', 'end_date')
    )
    op.create_index('idx_raw_disclosure_date_actual_date', 'raw_tushare_disclosure_date', ['actual_date'], unique=False)
    op.create_index('idx_raw_disclosure_date_end_date', 'raw_tushare_disclosure_date', ['end_date'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order
    op.drop_index('idx_raw_disclosure_date_end_date', table_name='raw_tushare_disclosure_date')
    op.drop_index('idx_raw_disclosure_date_actual_date', table_name='raw_tushare_disclosure_date')
    op.drop_table('raw_tushare_disclosure_date')

    op.drop_index('idx_raw_fina_mainbz_end_date', table_name='raw_tushare_fina_mainbz')
    op.drop_table('raw_tushare_fina_mainbz')

    op.drop_index('idx_raw_fina_audit_end_date', table_name='raw_tushare_fina_audit')
    op.drop_index('idx_raw_fina_audit_ann_date', table_name='raw_tushare_fina_audit')
    op.drop_table('raw_tushare_fina_audit')

    op.drop_index('idx_raw_express_end_date', table_name='raw_tushare_express')
    op.drop_index('idx_raw_express_ann_date', table_name='raw_tushare_express')
    op.drop_table('raw_tushare_express')

    op.drop_index('idx_raw_forecast_end_date', table_name='raw_tushare_forecast')
    op.drop_index('idx_raw_forecast_ann_date', table_name='raw_tushare_forecast')
    op.drop_table('raw_tushare_forecast')

    op.drop_index('idx_raw_dividend_record_date', table_name='raw_tushare_dividend')
    op.drop_index('idx_raw_dividend_div_proc', table_name='raw_tushare_dividend')
    op.drop_table('raw_tushare_dividend')

    op.drop_index('idx_raw_cashflow_end_date', table_name='raw_tushare_cashflow')
    op.drop_index('idx_raw_cashflow_ann_date', table_name='raw_tushare_cashflow')
    op.drop_table('raw_tushare_cashflow')

    op.drop_index('idx_raw_balancesheet_end_date', table_name='raw_tushare_balancesheet')
    op.drop_index('idx_raw_balancesheet_ann_date', table_name='raw_tushare_balancesheet')
    op.drop_table('raw_tushare_balancesheet')

    op.drop_index('idx_raw_income_end_date', table_name='raw_tushare_income')
    op.drop_index('idx_raw_income_ann_date', table_name='raw_tushare_income')
    op.drop_table('raw_tushare_income')

    op.drop_index('idx_raw_fina_indicator_end_date', table_name='raw_tushare_fina_indicator')
    op.drop_index('idx_raw_fina_indicator_ann_date', table_name='raw_tushare_fina_indicator')
    op.drop_table('raw_tushare_fina_indicator')
