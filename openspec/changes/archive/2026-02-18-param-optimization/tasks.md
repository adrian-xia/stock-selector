## 1. 数据库模型与迁移

- [x] 1.1 创建 `app/models/optimization.py`，定义 `OptimizationTask` 和 `OptimizationResult` 两个 SQLAlchemy 模型
- [x] 1.2 创建 Alembic 迁移文件，生成 `optimization_tasks` 和 `optimization_results` 两张表

## 2. 策略参数空间定义

- [x] 2.1 在 `StrategyMeta` dataclass 新增 `param_space: dict` 可选字段（默认空 dict）
- [x] 2.2 为 28 种策略补充 `param_space` 定义（在 factory.py 的 `_register()` 调用中添加）

## 3. 优化器核心

- [x] 3.1 创建 `app/optimization/__init__.py`
- [x] 3.2 创建 `app/optimization/base.py`，定义 `BaseOptimizer` 抽象基类和 `OptimizationResult` dataclass
- [x] 3.3 创建 `app/optimization/param_space.py`，实现 `generate_combinations()` 和 `count_combinations()` 工具函数
- [x] 3.4 创建 `app/optimization/grid_search.py`，实现 `GridSearchOptimizer`
- [x] 3.5 创建 `app/optimization/genetic.py`，实现 `GeneticOptimizer`

## 4. 优化 API

- [x] 4.1 创建 `app/api/optimization.py`，定义 Pydantic 请求/响应模型
- [x] 4.2 实现 `POST /api/v1/optimization/run` 端点（提交优化任务并后台执行）
- [x] 4.3 实现 `GET /api/v1/optimization/result/{task_id}` 端点
- [x] 4.4 实现 `GET /api/v1/optimization/list` 端点（分页查询）
- [x] 4.5 实现 `GET /api/v1/optimization/param-space/{strategy_name}` 端点
- [x] 4.6 在 `app/main.py` 注册 optimization_router

## 5. 前端页面

- [x] 5.1 创建 `web/src/api/optimization.ts`，封装优化相关 API 请求函数
- [x] 5.2 创建 `web/src/types/optimization.ts`，定义 TypeScript 类型
- [x] 5.3 创建 `web/src/pages/optimization/index.tsx`，实现参数优化页面（任务创建表单 + 任务列表 + 结果详情）
- [x] 5.4 更新 `web/src/App.tsx` 添加 `/optimization` 路由
- [x] 5.5 更新侧边栏导航菜单，新增"参数优化"入口

## 6. 单元测试

- [x] 6.1 创建 `tests/unit/test_param_space.py`，测试参数空间生成和组合计数
- [x] 6.2 创建 `tests/unit/test_grid_search.py`，测试网格搜索优化器（mock 回测引擎）
- [x] 6.3 创建 `tests/unit/test_genetic.py`，测试遗传算法优化器（mock 回测引擎）
- [x] 6.4 创建 `tests/unit/test_optimization_api.py`，测试 API 端点（mock 优化器）

## 7. 文档更新

- [x] 7.1 更新 `docs/design/00-概要设计-v2.md` 模块5 参数优化部分，标注为已实施
- [x] 7.2 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注参数优化为 V2 已实施
- [x] 7.3 更新 `README.md`，新增参数优化功能说明
- [x] 7.4 更新 `CLAUDE.md`，新增参数优化模块到目录结构和 V1 范围
- [x] 7.5 更新 `PROJECT_TASKS.md`，标记 Change 9 为已完成
