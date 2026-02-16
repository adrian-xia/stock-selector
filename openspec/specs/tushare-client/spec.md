## ADDED Requirements

### Requirement: TushareClient 实现 DataSourceClient Protocol
TushareClient SHALL 实现 `DataSourceClient` Protocol 的全部 4 个方法（`fetch_daily`, `fetch_stock_list`, `fetch_trade_calendar`, `health_check`），确保与现有 DataManager 兼容。

#### Scenario: 获取股票列表
- **WHEN** 调用 `fetch_stock_list()`
- **THEN** 返回全部 A 股列表，每条记录包含 ts_code/symbol/name/area/industry/market/list_date/list_status 字段

#### Scenario: 获取交易日历
- **WHEN** 调用 `fetch_trade_calendar(start_date, end_date)`
- **THEN** 返回指定日期范围内的交易日历，包含 cal_date/is_open/pre_trade_date 字段

#### Scenario: 获取日线数据
- **WHEN** 调用 `fetch_daily(code, start_date, end_date)`
- **THEN** 返回指定股票指定日期范围的日线数据，包含 OHLCV + adj_factor + turnover_rate 字段

#### Scenario: 健康检查
- **WHEN** 调用 `health_check()`
- **THEN** 通过调用 Tushare API 验证 token 有效性，返回 True/False

### Requirement: TushareClient 提供原始数据获取方法
TushareClient SHALL 提供 `fetch_raw_*` 系列方法，按日期获取全市场原始数据，返回 list[dict] 格式，字段与 Tushare API 输出一一对应。

#### Scenario: 按日期获取全市场日线
- **WHEN** 调用 `fetch_raw_daily(trade_date)`
- **THEN** 返回该交易日全市场 ~5000 条日线数据，字段包含 ts_code/trade_date/open/high/low/close/pre_close/change/pct_chg/vol/amount

#### Scenario: 按日期获取全市场复权因子
- **WHEN** 调用 `fetch_raw_adj_factor(trade_date)`
- **THEN** 返回该交易日全市场复权因子数据

#### Scenario: 按日期获取全市场每日指标
- **WHEN** 调用 `fetch_raw_daily_basic(trade_date)`
- **THEN** 返回该交易日全市场 PE/PB/换手率/市值等指标

#### Scenario: 按日期获取涨跌停价格
- **WHEN** 调用 `fetch_raw_stk_limit(trade_date)`
- **THEN** 返回该交易日全市场涨跌停价格

### Requirement: 令牌桶限流
TushareClient SHALL 使用令牌桶算法控制 API 调用频率，确保不超过 Tushare 的频率限制（500 次/分钟）。

#### Scenario: 高并发请求限流
- **WHEN** 短时间内发起超过 500 次 API 调用
- **THEN** 令牌桶自动等待，确保实际发送速率不超过配置的 QPS 限制（默认 480 次/分钟）

### Requirement: 重试机制
TushareClient SHALL 对 API 调用失败自动重试，支持配置重试次数和间隔。

#### Scenario: API 调用失败自动重试
- **WHEN** Tushare API 调用抛出异常
- **THEN** 自动重试最多 N 次（默认 3 次），每次间隔 M 秒（默认 1 秒）

#### Scenario: 重试耗尽后抛出异常
- **WHEN** 重试次数耗尽仍然失败
- **THEN** 抛出 `DataSyncError` 异常，包含原始错误信息

### Requirement: 异步包装
TushareClient SHALL 通过 `asyncio.to_thread` 将同步的 Tushare SDK 调用包装为异步方法，不阻塞事件循环。

#### Scenario: 异步调用不阻塞
- **WHEN** 在 async 上下文中调用 TushareClient 方法
- **THEN** SDK 的同步调用在线程池中执行，不阻塞事件循环
