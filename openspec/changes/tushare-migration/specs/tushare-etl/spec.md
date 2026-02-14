## ADDED Requirements

### Requirement: Tushare 股票基础信息清洗
系统 SHALL 提供 `transform_tushare_stock_basic` 函数，将 raw_tushare_stock_basic 数据清洗为 stocks 业务表格式。

#### Scenario: 日期格式转换
- **WHEN** 原始数据 list_date 为 "19910403"
- **THEN** 清洗后 list_date 为 date(1991, 4, 3)

#### Scenario: 退市日期处理
- **WHEN** 原始数据 delist_date 为 None 或空字符串
- **THEN** 清洗后 delist_date 为 None

### Requirement: Tushare 交易日历清洗
系统 SHALL 提供 `transform_tushare_trade_cal` 函数，将 raw_tushare_trade_cal 数据清洗为 trade_calendar 业务表格式。

#### Scenario: is_open 类型转换
- **WHEN** 原始数据 is_open 为整数 1
- **THEN** 清洗后 is_open 为布尔值 True

#### Scenario: pretrade_date 映射
- **WHEN** 原始数据 pretrade_date 为 "20260213"
- **THEN** 清洗后 pre_trade_date 为 date(2026, 2, 13)

### Requirement: Tushare 日线数据清洗（三表 JOIN）
系统 SHALL 提供 `transform_tushare_daily` 函数，将 raw_tushare_daily + raw_tushare_adj_factor + raw_tushare_daily_basic 三表 JOIN 后清洗为 stock_daily 业务表格式。

#### Scenario: 三表 JOIN 合并
- **WHEN** 同一 ts_code + trade_date 在三张 raw 表中都有数据
- **THEN** 清洗后的 stock_daily 记录包含 daily 的 OHLCV、adj_factor 的复权因子、daily_basic 的换手率

#### Scenario: amount 单位转换
- **WHEN** raw_tushare_daily 的 amount 为 460697.377（千元）
- **THEN** 清洗后 stock_daily 的 amount 为 460697377.0（元）

#### Scenario: 停牌状态判断
- **WHEN** raw_tushare_daily 的 vol 为 0 且 amount 为 0
- **THEN** 清洗后 trade_status 为 "0"（停牌）

#### Scenario: data_source 标记
- **WHEN** 数据来自 Tushare
- **THEN** stock_daily.data_source 为 "tushare"

### Requirement: Tushare 财务指标清洗
系统 SHALL 提供 `transform_tushare_fina_indicator` 函数，将 raw_tushare_fina_indicator 数据清洗为 finance_indicator 业务表格式。

#### Scenario: 字段映射
- **WHEN** 原始数据包含 roe=15.23, grossprofit_margin=45.6, netprofit_yoy=20.5
- **THEN** 清洗后 roe=15.23, gross_margin=45.6, profit_yoy=20.5

#### Scenario: report_type 推断
- **WHEN** 原始数据 end_date 为 "20250331"
- **THEN** 清洗后 report_type 为 "Q1"

### Requirement: Tushare 资金流向清洗
系统 SHALL 提供 `transform_tushare_moneyflow` 函数，将 raw_tushare_moneyflow 数据清洗为 money_flow 业务表格式。

#### Scenario: 字段一一对应
- **WHEN** 原始数据包含 buy_sm_vol/buy_sm_amount 等字段
- **THEN** 清洗后 money_flow 表对应字段正确填充

### Requirement: Tushare 龙虎榜清洗
系统 SHALL 提供 `transform_tushare_top_list` 函数，将 raw_tushare_top_list 数据清洗为 dragon_tiger 业务表格式。

#### Scenario: 买卖总额映射
- **WHEN** 原始数据 l_buy=1000000, l_sell=500000, net_amount=500000
- **THEN** 清洗后 buy_total=1000000, sell_total=500000, net_buy=500000
