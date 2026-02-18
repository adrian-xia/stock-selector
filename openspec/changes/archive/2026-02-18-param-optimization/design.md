## Context

系统已有 28 种选股策略（16 技术面 + 12 基本面），每种策略有 default_params（数值型参数）。现有回测引擎 `BacktestEngine.run()` 支持传入任意 strategy_params 执行单次回测，返回 sharpe_ratio、max_drawdown、annual_return 等绩效指标。

用户当前只能手动修改参数逐次回测，无法系统性地搜索最优参数组合。参数优化模块将自动化这一过程。

现有基础设施：
- `BacktestEngine.run()` — 异步回测，返回绩效指标
- `StrategyFactory` / `STRATEGY_REGISTRY` — 策略注册表，含 default_params
- `backtest_tasks` / `backtest_results` — 回测任务和结果表
- 前端：React 18 + Ant Design 5 + ECharts，已有 workbench 和 backtest 两个页面

## Goals / Non-Goals

**Goals:**
- G1: 提供网格搜索优化器，遍历参数空间所有组合，找到最优参数
- G2: 提供遗传算法优化器，高效搜索大参数空间
- G3: 优化任务持久化（数据库表），支持查询历史优化结果
- G4: 提供 HTTP API 提交优化任务、查询进度和结果
- G5: 前端参数优化页面，支持参数范围配置、任务提交、结果可视化

**Non-Goals:**
- 不做实时优化（盘中自动调参）
- 不做 Walk Forward Analysis（滚动窗口验证，V3 考虑）
- 不做分布式并行优化（单机执行）
- 不做贝叶斯优化等高级算法
- 不做优化结果自动应用到策略（用户手动采纳）

## Decisions

### D1: 优化器架构 — 基类 + 两种实现

采用 `BaseOptimizer` 抽象基类，定义 `optimize()` 接口，网格搜索和遗传算法分别实现。

```
BaseOptimizer (ABC)
├── GridSearchOptimizer    — 遍历所有参数组合
└── GeneticOptimizer       — 遗传算法搜索
```

**理由：** 统一接口便于扩展新算法，两种算法覆盖小参数空间（网格搜索精确）和大参数空间（遗传算法高效）。

### D2: 参数空间定义 — 在 StrategyMeta 中新增 param_space 字段

在 `StrategyMeta` dataclass 新增可选字段 `param_space: dict`，定义每个参数的类型、范围和步长：

```python
param_space = {
    "fast": {"type": "int", "min": 3, "max": 20, "step": 1},
    "slow": {"type": "int", "min": 10, "max": 60, "step": 5},
    "vol_ratio": {"type": "float", "min": 1.0, "max": 3.0, "step": 0.1},
}
```

**备选方案：** 单独的 param_space 注册表。
**选择理由：** 参数空间与策略强绑定，放在 StrategyMeta 中更内聚，API 查询时一次返回。

### D3: 优化目标 — 夏普比率为主，支持多指标排序

默认按夏普比率（Sharpe Ratio）排序，同时记录所有绩效指标（年化收益、最大回撤、胜率等），前端可切换排序维度。

**理由：** 夏普比率综合考虑收益和风险，是最常用的策略评价指标。

### D4: 执行方式 — 同步执行，后台任务

优化任务通过 API 提交后，在后台线程池中执行（复用 `asyncio.run_in_executor`）。任务状态通过数据库轮询查询。

**备选方案：** Celery 异步队列。
**选择理由：** 单机部署场景，线程池足够，避免引入额外依赖。与现有回测引擎执行方式一致。

### D5: 遗传算法参数

- 种群大小：20（默认）
- 最大代数：50（默认）
- 交叉率：0.8
- 变异率：0.1
- 选择方式：锦标赛选择（tournament_size=3）
- 适应度函数：夏普比率

用户可通过 API 覆盖这些超参数。

### D6: 前端页面 — 新增 optimization 页面

新增 `web/src/pages/optimization/` 页面，包含：
- 策略选择 + 参数范围配置表单
- 回测区间和股票池配置
- 优化算法选择（网格搜索 / 遗传算法）
- 任务列表（进度、状态）
- 结果展示：最优参数表格、参数热力图（ECharts heatmap）、回测对比

导航菜单新增"参数优化"入口。

### D7: 数据库表设计

新增 2 张表：

**optimization_tasks:**
- id, strategy_name, algorithm (grid/genetic), param_space (JSONB), stock_codes (JSONB)
- start_date, end_date, initial_capital
- ga_config (JSONB, 遗传算法超参数)
- status (pending/running/completed/failed), progress (int, 0-100)
- total_combinations (int), completed_combinations (int)
- error_message, created_at, updated_at

**optimization_results:**
- id, task_id (FK), rank (int)
- params (JSONB), sharpe_ratio, annual_return, max_drawdown, win_rate, total_trades
- total_return, volatility, calmar_ratio, sortino_ratio
- created_at

## Risks / Trade-offs

- [大参数空间网格搜索耗时过长] → 前端显示预估组合数，超过 1000 组合时建议使用遗传算法；API 层限制最大组合数 10000
- [回测引擎单线程瓶颈] → 优化器内部使用 `asyncio.gather` 并发执行多个回测（受限于 GIL，实际并发度取决于 IO）；Backtrader 的 `run_in_executor` 已在线程池中执行
- [遗传算法收敛不稳定] → 提供多次运行取最优的选项；记录每代最优适应度供分析
- [优化任务占用大量数据库空间] → 只保存 Top N 结果（默认 Top 20），不保存所有组合的回测明细
