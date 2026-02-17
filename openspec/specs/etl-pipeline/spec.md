## REMOVED Requirements

### Requirement: clean_baostock_daily
**Reason**: BaoStock 数据源已移除
**Migration**: 使用 transform_tushare_daily 替代

### Requirement: clean_akshare_daily
**Reason**: AKShare 数据源已移除
**Migration**: 使用 transform_tushare_daily 替代

### Requirement: clean_baostock_stock_list
**Reason**: BaoStock 数据源已移除
**Migration**: 使用 transform_tushare_stock_basic 替代

### Requirement: clean_baostock_trade_calendar
**Reason**: BaoStock 数据源已移除
**Migration**: 使用 transform_tushare_trade_cal 替代

## ADDED Requirements

### Requirement: Tushare ETL 清洗函数集
etl.py SHALL 提供完整的 Tushare 数据清洗函数集（transform_tushare_stock_basic, transform_tushare_trade_cal, transform_tushare_daily, transform_tushare_fina_indicator, transform_tushare_moneyflow, transform_tushare_top_list, transform_tushare_top_inst, transform_tushare_index_basic, transform_tushare_index_daily, transform_tushare_index_weight, transform_tushare_industry_classify, transform_tushare_industry_member, transform_tushare_index_technical），替代原有的 clean_baostock_* / clean_akshare_* 函数。

#### Scenario: 导入新的清洗函数
- **WHEN** 从 etl.py 导入清洗函数
- **THEN** transform_tushare_* 系列函数全部可用，clean_baostock_* / clean_akshare_* 已移除

### Requirement: normalize_stock_code 支持 tushare 源
normalize_stock_code SHALL 支持 source="tushare"，Tushare 原生代码格式（600519.SH）直接透传。

#### Scenario: Tushare 代码格式透传
- **WHEN** 调用 normalize_stock_code("600519.SH", source="tushare")
- **THEN** 返回 "600519.SH"（无需转换）
