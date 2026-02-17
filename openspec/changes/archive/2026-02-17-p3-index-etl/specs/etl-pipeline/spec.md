## MODIFIED Requirements

### Requirement: Tushare ETL 清洗函数集
etl.py SHALL 提供完整的 Tushare 数据清洗函数集（transform_tushare_stock_basic, transform_tushare_trade_cal, transform_tushare_daily, transform_tushare_fina_indicator, transform_tushare_moneyflow, transform_tushare_top_list, transform_tushare_top_inst, transform_tushare_index_basic, transform_tushare_index_daily, transform_tushare_index_weight, transform_tushare_industry_classify, transform_tushare_industry_member, transform_tushare_index_technical），替代原有的 clean_baostock_* / clean_akshare_* 函数。

#### Scenario: 导入新的清洗函数
- **WHEN** 从 etl.py 导入清洗函数
- **THEN** transform_tushare_* 系列函数全部可用，包括 P3 指数数据的 transform_tushare_index_basic、transform_tushare_index_daily、transform_tushare_index_weight、transform_tushare_industry_classify、transform_tushare_industry_member、transform_tushare_index_technical
