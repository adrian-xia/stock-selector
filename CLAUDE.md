# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 语言要求

对话全程中文

## 项目概述

面向个人投资者的 A 股智能选股与回测平台。单机部署、单人使用。
后端 Python 3.13 + FastAPI，前端 React 19 + TypeScript + Ant Design 6。

## 常用命令

### 后端

```bash
# 安装依赖
uv sync

# 启动开发服务器
uv run uvicorn app.main:app --reload

# 跳过启动时数据完整性检查（开发时常用）
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app --reload

# 数据库迁移
uv run alembic upgrade head                          # 执行迁移
uv run alembic revision --autogenerate -m "描述"    # 生成新迁移

# 数据管理 CLI
uv run python -m app.data.cli sync-daily             # 同步每日数据
uv run python -m app.data.cli init-tushare           # 交互式数据初始化向导
uv run python -m app.data.cli backfill-daily --start 2024-01-01 --end 2026-02-07
uv run python -m app.data.cli cleanup-delisted       # 清理退市股数据
```

### 测试

```bash
# pytest 配置在 pyproject.toml，asyncio_mode = "auto"
pytest tests/                                        # 全部测试
pytest tests/unit/                                   # 仅单元测试
pytest tests/integration/                            # 仅集成测试
pytest tests/unit/test_api_backtest_run.py           # 单个文件
pytest tests/unit/test_api_backtest_run.py::TestRunBacktestApi::test_invalid_date_range_returns_400  # 单个用例
pytest --cov=app tests/                              # 带覆盖率
```

### 前端

```bash
cd web
pnpm install                                         # 安装依赖
pnpm dev                                             # 开发服务器 http://localhost:5173
pnpm build                                           # 生产构建
pnpm lint                                            # ESLint 检查
tsc -b                                               # TypeScript 类型检查
```

前端开发时 Vite 代理 `/api` → `http://localhost:8000`。

## 核心架构

### 数据流（盘后链路）

每日收盘后自动执行的完整链路（`app/scheduler/jobs.py`）：

1. 数据嗅探 — 检测 Tushare 数据是否就绪（`app/data/probe.py`）
2. Raw 层同步 — 从 Tushare 拉取原始数据到 raw 表（`app/data/manager.py` → `sync_raw_daily`）
3. ETL 清洗 — raw 表 → 业务表（`app/data/etl.py` → `etl_daily`）
4. 技术指标计算 — 增量计算 MA/MACD/KDJ 等（`app/data/batch.py` → `compute_incremental`）
5. 策略执行 — Pipeline 执行已启用策略（`app/strategy/pipeline.py`）
6. 命中率回填 — 回填历史选股结果的 N 日收益率（`app/strategy/pipeline.py`）
7. 缓存刷新 — 刷新 Redis 缓存

核心入口：`sync_daily_by_date(dates)` — 按日期批量同步全市场数据（3 次 API 调用拉全市场）。

### 数据分层

- **Raw 层**（99 张表，`raw_` 前缀）— Tushare API 原始数据，按日期批量获取
- **业务层**（30+ 张表）— ETL 清洗后的结构化数据
- 分为 P0-P5 优先级：P0 基础行情、P1 财务、P2 资金流向、P3 指数、P4 板块、P5 扩展

### 策略引擎

- 35 种策略：23 技术面 + 12 基本面（`app/strategy/technical/` + `app/strategy/fundamental/`）
- 扁平继承自 `BaseStrategy`，通过工厂模式注册（`app/strategy/factory.py`）
- 策略注册制：盘后链路从 `strategies` 数据库表读取启用的策略
- Pipeline 执行：SQL 粗筛 → 技术面 → 基本面 → 加权排序（`app/strategy/pipeline.py`）
- 加权排序基于 5d 命中率（`strategy_hit_stats` 表），权重 [0.3, 3.0]
- 全市场选股回放优化：`app/optimization/market_optimizer.py`，历史回放评估参数组合
- 每周自动 cron（`app/scheduler/market_opt_job.py`），最佳参数自动写入 strategies 表

### API 路由

所有 API 挂载在 `/api/v1/` 前缀下，路由注册在 `app/main.py`。
主要模块：strategy、backtest、data、optimization、news、realtime、alert、websocket。

### 关键模式

- **令牌桶限流**：`app/data/tushare.py` 中的 TushareClient，400 QPS + 特殊接口独立限流桶
- **COPY 批量写入**：`app/data/copy_writer.py`，临时表 → COPY → UPSERT 三步法
- **Redis 降级**：Redis 不可用时自动降级到数据库直查
- **优雅关闭**：lifespan shutdown 阶段等待任务完成（30 秒超时）

## 技术栈

| 后端 | 前端 |
|------|------|
| Python 3.13 + FastAPI | React 19 + TypeScript |
| SQLAlchemy (async) + asyncpg | Ant Design 6 + ECharts 6 |
| PostgreSQL + TimescaleDB（可选） | Vite 7 + pnpm |
| Redis + hiredis | React Query 5 + Zustand 5 |
| Backtrader（回测） | React Router 7 |
| APScheduler（定时任务） | Axios |
| uv（包管理） | — |

## 编码规范

- Python 3.12+ 语法，所有函数必须有类型注解
- async/await 用于 IO 操作（数据库、API 调用）
- Pydantic v2 做数据校验，pydantic-settings 加载 `.env` 配置
- SQL 全部使用参数化查询，禁止字符串拼接
- 日志使用 Python logging，不用 print
- 所有代码需要详细的中文注释
- **每次完成功能变更，必须同步更新：**
  - `README.md` — 功能特性、技术栈、环境要求、配置说明、项目结构、测试数量
  - `CLAUDE.md` — 技术栈、V1 范围、目录结构
  - `.env.example` — 如果新增了配置项

## 设计文档

编码前必读 `docs/design/99-实施范围-V1与V2划分.md`。

| 模块 | 设计文档 |
|------|---------|
| 数据采集 | `docs/design/01-详细设计-数据采集.md` |
| 策略引擎 | `docs/design/02-详细设计-策略引擎.md` |
| AI 与回测 | `docs/design/03-详细设计-AI与回测.md` |
| 前端交互 | `docs/design/04-详细设计-前端与交互.md` |
| 定时任务 | `docs/design/10-系统设计-定时任务调度.md` |
| 缓存策略 | `docs/design/11-系统设计-缓存策略.md` |
| V1/V2 范围 | `docs/design/99-实施范围-V1与V2划分.md` |

V2 详细实施计划见 `PROJECT_TASKS.md`。

## 提交前强制检查清单

**每次 Git 提交前必须完成，不一致则拒绝提交：**

### 设计文档一致性

1. 确认变更涉及哪些模块，查阅对应设计文档
2. 对比实现与设计：功能说明、技术方案、表结构、API 接口、配置项
3. 处理不一致：
   - 实现符合设计 → 可以提交
   - 实现优化了设计 → **先更新设计文档**，再提交代码
   - 实现偏离了设计 → **拒绝提交**，重新实现或修改设计文档
   - 新增功能（设计文档未提及）→ **先补充设计文档**
   - V2 功能提前实施 → 更新 `99-实施范围-V1与V2划分.md` 和 `PROJECT_TASKS.md`

### 文档同步

- [ ] `README.md` 已更新
- [ ] `CLAUDE.md` 已更新
- [ ] `.env.example` 已更新（如有新配置项）
- [ ] `docs/design/` 相关文档已更新
- [ ] `PROJECT_TASKS.md` 已更新（如涉及 V2 计划调整）

### 拒绝提交的情况

- 实现与设计文档不一致，且未更新设计文档
- 新增了数据库表/字段/API 接口，但设计文档未说明
- README.md 或 CLAUDE.md 未同步更新

### 提交信息

- Commit message 需清晰描述变更内容
- 包含 `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`

## OpenSpec 工作流

本项目使用 OpenSpec 管理开发流程（`openspec/` 目录）：

1. `/opsx:new <feature-name>` — 创建变更
2. `/opsx:ff` — 生成 proposal → specs → design → tasks
3. `/opsx:apply` — 按 tasks 逐步实现
4. `/opsx:archive` — 归档完成的变更

## 部署

```bash
# 打包
uv run python -m scripts.package

# 服务器部署
uv sync && uv run alembic upgrade head && uv run python -m scripts.init_data
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 不做

用户权限、高手跟投。
