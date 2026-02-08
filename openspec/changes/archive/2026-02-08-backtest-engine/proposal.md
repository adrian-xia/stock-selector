## Why

策略引擎已完成，能从 5000+ 只股票中筛选出候选池，但用户无法验证策略的历史表现。回测引擎是策略有效性验证的核心模块——它在历史数据上模拟交易，输出年化收益、最大回撤、夏普比率等绩效指标，帮助用户判断策略是否值得实盘跟踪。前端回测结果页和 AI 分析模块都直接依赖回测引擎，必须先行实现。

## What Changes

- 新增 `BacktestEngine` 回测执行引擎，基于 Backtrader 框架，封装 Cerebro 配置、数据加载、策略执行和结果提取
- 新增 `AStockStrategy` 回测策略基类，内置 A 股涨跌停检查逻辑（主板 ±10%、创业板/科创板 ±20%）
- 新增 `PriceLimitChecker` 涨跌停检查器，在下单前拦截无法成交的订单
- 新增 `ChinaStockCommission` A 股佣金模型（佣金万 2.5 + 印花税千 1）
- 新增 `PandasDataPlus` 自定义 DataFeed，支持换手率、复权因子等扩展字段
- 新增 `BacktestResultWriter` 结果写入器，将绩效指标、交易明细和净值曲线写入数据库
- 新增回测 HTTP API：`POST /api/v1/backtest/run`（同步执行）、`GET /api/v1/backtest/result/{task_id}`（查询结果）
- V1 简化：同步执行（无 Redis 队列/Worker），等权重分配，状态机仅 pending → running → completed/failed

## Capabilities

### New Capabilities
- `backtest-engine`: 回测执行引擎核心，包括 Cerebro 配置、数据加载（前复权）、策略执行、绩效分析器（Analyzers）配置
- `backtest-strategy`: A 股回测策略基类，涨跌停检查器，A 股佣金模型，停牌处理
- `backtest-result-writer`: 回测结果提取与持久化，从 Analyzers 提取指标，trades/equity_curve 写入 JSONB
- `backtest-api`: 回测 HTTP API 端点，Pydantic 请求/响应模型，任务状态管理

### Modified Capabilities
（无——回测引擎是全新模块，不修改现有 spec 的需求定义）

## Impact

- **新增目录：** `app/backtest/`（engine.py、strategy.py、price_limit.py、commission.py、data_feed.py、writer.py）、`app/api/backtest.py`
- **依赖模块：** 消费 `data-manager` 的 `get_daily_bars()` 接口获取历史日线数据；消费 `strategy-factory` 的 `get_strategy()` 实例化策略
- **数据库：** 读写 `backtest_tasks` 和 `backtest_results` 表（已建表）
- **第三方依赖：** Backtrader（需确认 pyproject.toml 中已添加）
- **HTTP API：** 新增 `/api/v1/backtest/` 路由组
- **后续模块依赖：** 前端回测结果页需要调用回测 API；AI 分析模块可能参考回测绩效
