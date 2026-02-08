## ADDED Requirements

### Requirement: 回测策略基类测试覆盖
系统 SHALL 为 AStockStrategy 和 SignalStrategy 提供单元测试，验证涨跌停拦截、净值记录和交易日志。

#### Scenario: AStockStrategy 涨停拦截买入
- **WHEN** 当前价格触及涨停（涨幅 >= limit_pct）时调用 safe_buy
- **THEN** 返回 None，不下买单

#### Scenario: AStockStrategy 正常买入
- **WHEN** 当前价格未涨停时调用 safe_buy
- **THEN** 成功下买单

#### Scenario: AStockStrategy 跌停拦截卖出
- **WHEN** 当前价格触及跌停（跌幅 >= limit_pct）时调用 safe_sell
- **THEN** 返回 None，不下卖单

#### Scenario: AStockStrategy 净值曲线记录
- **WHEN** 策略运行多个 bar
- **THEN** equity_curve 列表长度等于 bar 数量，每条记录包含 date 和 value

#### Scenario: AStockStrategy 交易日志记录
- **WHEN** 发生买入和卖出交易
- **THEN** trades_log 包含对应的 buy 和 sell 记录，含 stock_code、price、size、pnl

#### Scenario: SignalStrategy 首日买入
- **WHEN** 策略开始运行且有足够资金
- **THEN** 在首个可交易日全仓买入（100 股整数倍）

#### Scenario: SignalStrategy 持有天数到期卖出
- **WHEN** 持仓达到 hold_days 天
- **THEN** 卖出全部持仓

#### Scenario: SignalStrategy 止损卖出
- **WHEN** 持仓亏损超过 stop_loss_pct
- **THEN** 提前卖出全部持仓

#### Scenario: SignalStrategy 停牌日不操作
- **WHEN** 当日成交量为 0（停牌）
- **THEN** 不执行任何买卖操作

### Requirement: 回测数据加载测试覆盖
系统 SHALL 为 data_feed.py 的数据加载和 DataFeed 构建提供单元测试。

#### Scenario: load_stock_data 正常加载并前复权
- **WHEN** 数据库返回含 adj_factor 的日线数据
- **THEN** 返回的 DataFrame 中 OHLC 价格已应用前复权公式（price * adj_factor / latest_adj_factor）

#### Scenario: load_stock_data 无数据返回空 DataFrame
- **WHEN** 数据库查询结果为空
- **THEN** 返回空 DataFrame

#### Scenario: build_data_feed 字段映射正确
- **WHEN** 传入包含 turnover_rate 和 adj_factor 列的 DataFrame
- **THEN** 返回的 PandasDataPlus 实例正确映射这些字段
