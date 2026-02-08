## 1. 项目配置与模块骨架

- [x] 1.1 在 `pyproject.toml` 中添加 `backtrader` 依赖，运行 `uv sync` 安装
- [x] 1.2 创建 `app/backtest/` 目录结构：`__init__.py`、`engine.py`、`strategy.py`、`price_limit.py`、`commission.py`、`data_feed.py`、`writer.py`

## 2. A 股交易规则组件

- [x] 2.1 实现 `PriceLimitChecker`（`price_limit.py`）：`get_limit_pct(ts_code, name)` 根据板块返回涨跌停幅度，`is_limit_up(close, pre_close, limit_pct)` 和 `is_limit_down(close, pre_close, limit_pct)` 判断函数
- [x] 2.2 实现 `ChinaStockCommission`（`commission.py`）：继承 `bt.CommInfoBase`，佣金万 2.5（最低 5 元）+ 卖出印花税千 1
- [x] 2.3 实现 `PandasDataPlus`（`data_feed.py`）：继承 `bt.feeds.PandasData`，添加 `turnover_rate`、`adj_factor` 扩展 lines

## 3. 数据加载

- [x] 3.1 实现 `load_stock_data()` 异步函数（`data_feed.py`）：查询 `stock_daily` 表，应用动态前复权（`adj_factor / latest_adj_factor`），返回 DataFrame
- [x] 3.2 实现 `build_data_feed()` 函数：将 DataFrame 转换为 `PandasDataPlus` 实例，设置正确的列映射

## 4. 回测策略

- [x] 4.1 实现 `AStockStrategy` 基类（`strategy.py`）：继承 `bt.Strategy`，集成 `PriceLimitChecker`，`next()` 中记录 equity_curve，提供 `safe_buy()` / `safe_sell()` 方法（内含涨跌停检查）
- [x] 4.2 实现 `SignalStrategy`（`strategy.py`）：继承 `AStockStrategy`，params 包含 `hold_days=5` 和 `stop_loss_pct=0.05`，实现买入/持有/止损逻辑

## 5. 回测引擎核心

- [x] 5.1 实现 `BacktestEngine` 类（`engine.py`）：`__init__` 接收 `session_factory`，`run()` 方法配置 Cerebro（资金、佣金、滑点、Analyzers），加载数据，执行回测
- [x] 5.2 实现等权重仓位计算：`shares = floor(cash / n_stocks / price / 100) * 100`
- [x] 5.3 实现 `async run_backtest()` 包装函数：用 `run_in_executor` 在线程池中执行同步的 `BacktestEngine.run()`

## 6. 结果写入

- [x] 6.1 实现 `BacktestResultWriter`（`writer.py`）：从 Analyzers 提取绩效指标（sharpe_ratio、max_drawdown、total_return、annual_return、win_rate、total_trades、profit_loss_ratio）
- [x] 6.2 实现手动计算指标：calmar_ratio、volatility（从 equity_curve 计算日收益率标准差年化）
- [x] 6.3 实现 trades 提取：从 `notify_trade` 记录中序列化为 JSON 列表
- [x] 6.4 实现 equity_curve 序列化：`[{"date": "2024-01-02", "value": 1000000.0}, ...]`
- [x] 6.5 实现任务状态更新：成功时 `status='completed'`，失败时 `status='failed'` + `error_message`

## 7. HTTP API

- [x] 7.1 创建 `app/api/backtest.py`：定义 Pydantic 请求模型 `BacktestRunRequest`（strategy_name、strategy_params、stock_codes、start_date、end_date、initial_capital）和响应模型
- [x] 7.2 实现 `POST /api/v1/backtest/run` 端点：校验参数 → 创建 task 记录 → 调用 `run_backtest()` → 写入结果 → 返回响应
- [x] 7.3 实现 `GET /api/v1/backtest/result/{task_id}` 端点：查询 task + result，返回完整结果（含 trades 和 equity_curve）
- [x] 7.4 在 `app/main.py` 中注册回测 API 路由

## 8. 单元测试

- [x] 8.1 编写 `tests/unit/test_price_limit.py`：测试各板块涨跌停判断（主板、创业板、科创板、ST）
- [x] 8.2 编写 `tests/unit/test_commission.py`：测试佣金计算（买入、卖出含印花税、最低佣金）
- [x] 8.3 编写 `tests/unit/test_backtest_engine.py`：测试 BacktestEngine 基本流程（使用构造的 DataFrame，不依赖数据库）
- [x] 8.4 编写 `tests/unit/test_result_writer.py`：测试绩效指标提取和 JSON 序列化逻辑
