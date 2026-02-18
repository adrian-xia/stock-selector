## Why

当前系统提供 28 种选股策略，每种策略都有默认参数，但不同市场环境下最优参数差异很大。用户只能手动调整参数并逐次回测，效率低且难以找到全局最优解。参数优化模块通过自动化搜索，帮助用户快速找到最优策略参数组合，提升策略收益。

## What Changes

- 新增网格搜索优化器：定义参数空间（min/max/step），遍历所有组合，批量调用回测引擎，按夏普比率排序输出最优参数
- 新增遗传算法优化器：适应度函数（夏普比率）、交叉/变异/选择算子，适用于大参数空间的高效搜索
- 新增优化任务管理：`optimization_tasks` + `optimization_results` 数据库表，记录任务状态、进度和结果
- 新增优化 API：提交优化任务、查询进度、获取结果
- 新增前端参数优化页面：策略选择、参数范围配置、任务提交、进度展示、结果可视化（参数热力图、最优参数推荐、回测对比）

## Capabilities

### New Capabilities
- `param-optimization-engine`: 参数优化算法核心（网格搜索 + 遗传算法），定义参数空间、执行批量回测、排序输出最优参数
- `param-optimization-api`: 参数优化 HTTP API（提交任务、查询进度、获取结果列表）
- `param-optimization-models`: 优化任务和结果的数据库模型（optimization_tasks、optimization_results）+ Alembic 迁移
- `param-optimization-frontend`: 前端参数优化页面（参数配置、任务管理、结果可视化）

### Modified Capabilities
- `strategy-factory`: 新增 `get_param_space(name)` 方法，返回策略的可优化参数空间定义

## Impact

- 新增模块：`app/optimization/`（优化器核心）
- 新增 API：`app/api/optimization.py`（`/api/v1/optimization/*`）
- 新增模型：`app/models/optimization.py`（2 张表）
- 新增前端页面：`web/src/pages/optimization/`
- 修改：`app/strategy/factory.py`（新增参数空间定义）
- 修改：`app/main.py`（注册新路由）
- 修改：`web/src/`（路由、导航菜单）
- 依赖：复用现有 `BacktestEngine.run()` 进行批量回测
- 新增 Alembic 迁移文件
