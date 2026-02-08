## Context

策略引擎（12 种策略 + Pipeline 5 层漏斗）已完成，能筛选出候选股票池。数据库中已有 `backtest_tasks` 和 `backtest_results` 两张表（含 trades_json 和 equity_curve_json JSONB 字段）。DataManager 提供 `get_daily_bars()` 查询历史日线数据。

现有依赖：
- `DataManager.get_daily_bars(ts_code, start_date, end_date)` — 查询日线数据
- `StrategyFactory.get_strategy(name, params)` — 实例化选股策略
- `backtest_tasks` 表 — 回测任务配置（已建表）
- `backtest_results` 表 — 回测结果（已建表，含 JSONB 字段）
- `stock_daily` 表 — 含 adj_factor 复权因子

约束：
- Backtrader 尚未安装，需添加到 pyproject.toml
- V1 同步执行，不用 Redis 队列
- Backtrader 是同步框架，需要在 async API 中用 `run_in_executor` 调用

## Goals / Non-Goals

**Goals:**
- 基于 Backtrader 实现完整的单股/多股回测流程
- 正确处理 A 股特有规则：涨跌停限制、佣金/印花税、前复权、停牌
- 从 Analyzers 提取绩效指标并持久化到数据库
- 提供同步执行的 HTTP API，前端可直接获取结果
- 防未来函数：`cheat_on_open=False`，财务数据用 ann_date 过滤

**Non-Goals:**
- 不实现 Redis 队列和异步 Worker（V1 同步执行）
- 不实现评分加权和风险平价仓位分配（V1 仅等权重）
- 不实现策略参数优化（V2 范围）
- 不实现回测任务取消功能（V1 状态机简化）
- 不实现回测结果的图表渲染（前端负责）

## Decisions

### Decision 1: 同步执行 vs 异步队列

**选择：同步执行 + run_in_executor**

- 设计文档定义了 Redis 队列 + BacktestWorker 异步执行模式
- V1 单人使用，不存在并发回测需求，同步执行足够
- Backtrader 是同步框架，在 FastAPI 的 async 端点中用 `asyncio.get_event_loop().run_in_executor()` 包装
- API 端点同步等待回测完成后返回结果，前端无需轮询
- V2 如果需要支持长时间回测（>30s），再引入队列

### Decision 2: 数据加载 — 直接查库 vs 通过 DataManager

**选择：直接查库构建 DataFrame**

- Backtrader 需要 pandas DataFrame 格式的 OHLCV 数据
- DataManager 的 `get_daily_bars()` 返回 ORM 对象列表，还需转换
- 回测模块直接用 SQL 查询 stock_daily 表，一步到位构建 DataFrame
- 前复权在查询后立即应用：`price_adj = price_raw * (adj_factor / latest_adj_factor)`

### Decision 3: 涨跌停检查 — Backtrader Sizer vs 自定义 Checker

**选择：自定义 PriceLimitChecker + AStockStrategy 基类**

- Backtrader 默认不处理涨跌停，会在涨停价买入、跌停价卖出
- 在 `AStockStrategy.next()` 中下单前调用 PriceLimitChecker 检查
- 涨停判断：`close >= pre_close * (1 + limit_pct) - 0.01`（考虑四舍五入）
- 跌停判断：`close <= pre_close * (1 - limit_pct) + 0.01`
- 板块涨跌停幅度：主板 10%、创业板/科创板 20%（通过股票代码前缀判断）

### Decision 4: 佣金模型

**选择：自定义 ChinaStockCommission**

- A 股佣金：买卖双向万 2.5（最低 5 元）
- 印花税：卖出千 1（买入不收）
- 过户费：忽略（金额极小）
- 滑点：固定千 1（`broker.set_slippage_perc(0.001)`）

### Decision 5: 回测策略与选股策略的关系

**选择：独立的 Backtrader 策略类，引用选股策略做信号**

- 选股策略（BaseStrategy.filter_batch）是批量筛选接口，输入全市场 DataFrame
- 回测策略（AStockStrategy）是 Backtrader 的 bt.Strategy 子类，逐 bar 执行
- 回测时不直接调用 filter_batch，而是将选股策略的逻辑转化为 Backtrader 的买卖信号
- V1 简化方案：回测策略接收 `strategy_name` 和 `params`，在 `next()` 中根据技术指标判断买卖
- 提供一个通用的 `SignalStrategy`：买入条件 = 选股策略命中，卖出条件 = 持有 N 天或止损

### Decision 6: 绩效指标提取

**选择：使用 Backtrader 内置 Analyzers + 手动补充**

- 内置 Analyzers：SharpeRatio、DrawDown、TradeAnalyzer、Returns
- 手动计算：Calmar Ratio、Sortino Ratio、Alpha/Beta（对比沪深 300）
- 交易明细：从 TradeAnalyzer 提取，序列化为 JSON 存入 trades_json
- 净值曲线：在 `next()` 中每日记录 broker.getvalue()，存入 equity_curve_json

### Decision 7: 目录结构

```
app/backtest/
├── __init__.py
├── engine.py          # BacktestEngine：Cerebro 配置、执行入口
├── strategy.py        # AStockStrategy 基类 + SignalStrategy
├── price_limit.py     # PriceLimitChecker 涨跌停检查
├── commission.py      # ChinaStockCommission A 股佣金
├── data_feed.py       # PandasDataPlus 自定义 DataFeed + 数据加载
└── writer.py          # BacktestResultWriter 结果写入
app/api/
└── backtest.py        # HTTP API 路由
```

### Decision 8: 多股票回测 — 等权重分配

**选择：V1 仅等权重**

- 用户提交多只股票代码，资金按股票数量等分
- 每只股票独立执行买卖信号，互不影响
- Backtrader 支持多 Data Feed，每只股票一个 Feed
- 仓位计算：`position_size = total_cash / n_stocks / current_price`（取整到 100 股）

## Risks / Trade-offs

- **[性能] 同步执行阻塞 API** → V1 单人使用可接受。回测 1 年日线数据约 1-3 秒，10 年约 10-30 秒。超过 30 秒的场景（多股票 + 长周期）V2 再用队列优化
- **[精度] 前复权动态计算** → 使用 `adj_factor / latest_adj_factor` 动态前复权，每次回测时重新计算，确保复权因子更新后结果一致
- **[兼容性] Backtrader 维护状态** → Backtrader 最后更新于 2021 年，但功能稳定，A 股回测社区广泛使用。如果未来遇到 Python 兼容性问题，可考虑迁移到 vnpy 或自研
- **[简化] 选股策略到回测信号的转换** → V1 用通用 SignalStrategy（持有 N 天 + 止损），无法完全复现选股策略的复杂逻辑。V2 可以为每种选股策略编写对应的 Backtrader 策略
- **[A 股规则] 涨跌停判断精度** → 使用 0.01 元容差处理四舍五入，覆盖绝大多数场景。极端情况（如 ST 股 ±5%）通过股票名称前缀判断
