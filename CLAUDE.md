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
uv run python -m app.data.cli fix-integrity          # 修复数据完整性（重建指数/板块技术指标）
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
4. 技术指标计算 — 增量计算 MA/MACD/KDJ/滚动最高价等 31 项指标（`app/data/batch.py` → `compute_incremental`）
5. 策略执行 — Pipeline 执行已启用策略（`app/strategy/pipeline.py`）
6. 命中率回填 — 回填历史选股结果的 N 日收益率（`app/strategy/pipeline.py`）
7. 缓存刷新 — 刷新 Redis 缓存
8. ⭐ StarMap 投研（`app/research/orchestrator.py`，开发中）

核心入口：`sync_daily_by_date(dates)` — 按日期批量同步全市场数据（3 次 API 调用拉全市场）。

### 数据分层

- **Raw 层**（99 张表，`raw_` 前缀）— Tushare API 原始数据，按日期批量获取
- **业务层**（30+ 张表）— ETL 清洗后的结构化数据
- 分为 P0-P5 优先级：P0 基础行情、P1 财务、P2 资金流向、P3 指数、P4 板块、P5 扩展

### 策略引擎

**V1 架构**（当前生产）：
- 36 种策略：24 技术面 + 12 基本面（`app/strategy/technical/` + `app/strategy/fundamental/`）
- 扁平继承自 `BaseStrategy`，通过工厂模式注册（`app/strategy/factory.py`）
- 策略注册制：盘后链路从 `strategies` 数据库表读取启用的策略
- Pipeline 执行：SQL 粗筛 → 技术面 → 基本面 → 加权排序（`app/strategy/pipeline.py`）
- 加权排序基于 5d 命中率（`strategy_hit_stats` 表），权重 [0.3, 3.0]
- 全市场选股回放优化：`app/optimization/market_optimizer.py`，历史回放评估参数组合
- Pipeline 缓存加速：Layer 1-2 结果写入 `pipeline_cache` 表，同一天多参数组合共享，实测 300x+ 加速
- 基本面优化器补充：缓存模式下按交易日复用财务字段，且无基本面策略时跳过财务补充，避免 Layer 3 反复查询拖慢任务
- 每周自动 cron（`app/scheduler/market_opt_job.py`），最佳参数自动写入 strategies 表

**V2 架构**（开发中，设计文档：`docs/design/20-策略引擎V2-全新设计.md`）：
- 策略角色分层：guard（排雷）/scorer（评分）/tagger（标签）/trigger（信号）/confirmer（确认）
- 36 → 20 策略：9 个淘汰、7 个合并、5 个降级为 confirmer
- 新 Pipeline：Layer 0（SQL）→ Layer 1（质量底池）→ Layer 2（信号触发）→ Layer 3（多因子融合）→ Layer 4（AI 终审）
- 市场状态感知：牛市/熊市/震荡市自适应权重
- 双注册表：`STRATEGY_REGISTRY`（V1）+ `STRATEGY_REGISTRY_V2`（V2）并存
- 基类：`BaseStrategy`（V1）+ `BaseStrategyV2`（V2）向后兼容
- 适配器模式：`GuardAdapter`/`TaggerAdapter` 包装 V1 策略为 V2 角色
- 已实现：
  - 1 个 Scorer（质量评分 0-100）
  - 5 个 Confirmer（加分系数 0.0-1.0）
  - 2 个 Guard（财务安全、现金流质量）
  - 2 个 Tagger（成长风格、红利风格）
  - 10 个 Trigger（4 进攻组 + 4 趋势组 + 2 底部组）
- 实施进度：Phase 2/7 完成（策略适配与重写）

### API 路由

所有 API 挂载在 `/api/v1/` 前缀下，路由注册在 `app/main.py`。
主要模块：strategy、backtest、data、optimization、news、realtime、alert、websocket。

### 关键模式

- **令牌桶限流**：`app/data/tushare.py` 中的 TushareClient，400 QPS + 特殊接口独立限流桶
- **COPY 批量写入**：`app/data/copy_writer.py`，临时表 → COPY → UPSERT 三步法
- **Redis 降级**：Redis 不可用时自动降级到数据库直查
- **优雅关闭**：lifespan shutdown 阶段等待任务完成（30 秒超时）
- **任务状态回收**：`run_post_market_chain` 所有退出路径（非交易日/锁占用/异常）均调用 `TaskLogger.finish()`，防止僵尸 running 记录

## 技术栈

| 后端 | 前端 |
|------|------|
| Python 3.13 + FastAPI | React 19 + TypeScript |
| SQLAlchemy (async) + asyncpg | Ant Design 6 + ECharts 6 |
| PostgreSQL + TimescaleDB（可选） | Vite 7 + pnpm |
| Redis + hiredis | React Query 5 + Zustand 5 |
| Backtrader（回测） | React Router 7 |
| Gemini Flash / Codex（AI 分析） | Axios |
| APScheduler（定时任务） | — |
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

所有设计文档已归档到 `docs/design/archived/`。

### 已归档文档（`docs/design/archived/`）

| 模块 | 设计文档 |
|------|---------|
| **StarMap 盘后投研系统** | `archived/18-starmap/` 目录（详细设计 + PoC 结果，Phase 0-4 基本完成） |
| 数据采集 | `archived/01-详细设计-数据采集.md` |
| 策略引擎 | `archived/02-详细设计-策略引擎.md` |
| AI 与回测 | `archived/03-详细设计-AI与回测.md` |
| 前端交互 | `archived/04-详细设计-前端与交互.md` |
| 量价综合策略 | `archived/05-详细设计-量价综合选股策略.md` |
| 定时任务 | `archived/10-系统设计-定时任务调度.md` |
| 缓存策略 | `archived/11-系统设计-缓存策略.md` |
| Pipeline 缓存优化 | `archived/12-系统设计-Pipeline缓存优化.md` |
| 测试策略 | `archived/13-系统设计-测试策略.md` |
| V4 量价优化任务 | `archived/14-系统设计-V4量价配合策略优化任务.md` |
| 高位回落企稳策略 | `archived/15-策略设计-高位回落企稳二次启动.md` |
| V1/V2 范围 | `archived/99-实施范围-V1与V2划分.md` |
| 项目总体计划 | `archived/99-项目总体计划.md` |
| V3 概要设计 | `archived/00-V3概要设计.md` |
| V3 实施计划 | `archived/01-V3实施计划.md` |
| V2 概要设计 | `archived/00-概要设计-v2.md` |
| 设计补全任务 | `archived/task-设计补全.md` |
| V3 规划文档 | `archived/v3_planning/` 目录（2 个文档） |
| V4 量价配合策略（完整） | `archived/v4_planning/` 目录（4 个文档，85% 已实现） |

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

# Docker 部署
docker-compose up -d --build  # 构建并启动容器（前后端 + supervisord）
docker-compose logs -f  # 查看日志
docker-compose down  # 停止服务

# Docker 注意事项
# - 容器时区已设置为 Asia/Shanghai，确保定时任务正确执行
# - 需要外部 PostgreSQL 和 Redis，通过 host.docker.internal 访问宿主机
# - 修改 Dockerfile 后需要 --build 重新构建镜像
```

## 跨会话进度追踪

**⚡ 每次新会话开始时，必须先读取 `PROJECT_TASKS.md`**。该文件包含 V4 StarMap 的详细 checkpoint 进度（Phase 0~4，27 个子任务 checkbox）。完成工作后务必更新对应 checkbox。

当前阶段：V4 StarMap 实施中。设计文档 `docs/design/18-盘后自动投研与交易计划系统设计-详细版.md`（V5 已封版）。

## 不做

用户权限、高手跟投、测试机械补全、前端骨架打磨、调度器锦上添花、V2 79 策略补全、设计文档补全。
