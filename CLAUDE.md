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
5. 策略执行 — V2 Pipeline 执行已启用 trigger（`app/strategy/pipeline_v2.py`）
6. 命中率回填 — 回填 `strategy_picks` 的 N 日收益率（`app/data/manager.py` / 调度链路）
7. 缓存刷新 — 刷新 Redis 缓存
8. ⭐ StarMap 投研（`app/research/orchestrator.py`，已接入生产主链）

当前默认调度口径：
- 盘后主链 / 自动数据更新默认周一至周五 `18:00`
- 数据嗅探默认补探到 `19:00`
- StarMap 独立 cron 默认周一至周五 `18:40`，仅作兜底；若主链已执行过当日 StarMap，则自动跳过重复执行

核心入口：`sync_daily_by_date(dates)` — 按日期批量同步全市场数据（3 次 API 调用拉全市场）。

### 数据分层

- **Raw 层**（99 张表，`raw_` 前缀）— Tushare API 原始数据，按日期批量获取
- **业务层**（30+ 张表）— ETL 清洗后的结构化数据
- 分为 P0-P5 优先级：P0 基础行情、P1 财务、P2 资金流向、P3 指数、P4 板块、P5 扩展

### 策略引擎

**当前生产架构**（设计文档：`docs/design/20-策略引擎V2-全新设计.md`）：
- 策略角色分层：guard（排雷）/scorer（评分）/tagger（标签）/trigger（信号）/confirmer（确认）
- 策略集合已完成 36 → 20 精简：9 个淘汰、7 个合并、5 个降级为 confirmer
- 当前主路径为 20 个 V2 策略：
  - 1 个 Scorer（质量评分 0-100）
  - 5 个 Confirmer（加法 bonus 0.2/0.3，支持 applicable_groups 信号组过滤，封顶 0.6）
  - 2 个 Guard（财务安全、现金流质量）
  - 2 个 Tagger（成长风格、红利风格，支持 style_strength 0.0-1.0）
  - 10 个 Trigger（4 进攻组 + 4 趋势组 + 2 底部组）
- Pipeline：Layer 0（SQL 硬过滤）→ Layer 1（质量底池）→ Layer 2（信号触发）→ Layer 3（多因子融合）
- 多因子融合包含：市场状态系数、rolling_performance 乘数（收敛到 `[0.8, 1.2]`）、style bonus、confirmer additive bonus
- 盘后调度、工作台 API、参数优化、策略配置页都已切到 V2
- `app/optimization/market_optimizer.py` 仅优化 V2 trigger，目标为命中率 + 盈亏比 − 回撤
- V1 主执行链路和旧策略文件已删除；仅保留：
  - `volume-price-pattern`（V4 独立策略，通过 `v4_daily_runner` 纳入日常选股落库流程）
  - `cashflow_quality` / `financial_safety` / `high_dividend` / `low_pe_high_roe` 四个基础策略供 adapter 复用
- `strategies` 表启动时会同步活跃策略，并物理清理废弃 V1 策略及其关联历史
- P4 板块日线 `sync_concept_daily()` 已接入最近 7 天缺口补追；若当天板块数据晚于股票数据落地，可在后续交易日盘后自动补齐最近缺口

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
| Codex（AI 分析） | Axios |
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
  - `CLAUDE.md` — 技术栈、当前策略架构、目录结构
  - `.env.example` — 如果新增了配置项

## 设计文档

所有设计文档已归档到 `docs/design/archived/`。

### 已归档文档（`docs/design/archived/`）

| 模块 | 设计文档 |
|------|---------|
| **StarMap 盘后投研系统** | `archived/18-starmap/` 目录（详细设计 + PoC 结果；当前代码已接入主链并作为统一计划层） |
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

当前阶段：V2/V4 → StarMap 统一链路已落地，StarMap 为唯一计划层与 Markdown/Telegram 报告输出层。设计文档 `docs/design/18-盘后自动投研与交易计划系统设计-详细版.md`（V5 已封版）。

## 项目长期约定（会话记忆落地）

以下内容视为当前项目的稳定口径；后续新会话默认按此理解，除非用户明确要求调整并同步更新文档/代码。

### 一、当前生产主链

- 日常生产主链统一为：`V2 Pipeline + V4 Daily Runner -> strategy_picks -> StarMap -> trade_plan_daily_ext`
- `V2 Pipeline` 是当前生产主执行链，负责 20 个 V2 策略的日常选股
- `V4 Daily Runner` 是独立专题链，负责 `volume-price-pattern` 的日常命中，不并入 `Pipeline V2`
- `V2` 与 `V4` 的日常命中结果都统一落入 `strategy_picks`
- `StarMap` 基于 `strategy_picks` 做盘后投研融合，并生成最终计划

### 二、计划层与报告层口径

- `StarMap` 是唯一计划层，不再保留并行的旧交易计划链路
- 最终增强交易计划统一写入 `trade_plan_daily_ext`
- 工作台/API/盘后总览默认读取 `trade_plan_daily_ext`
- `StarMap` 同时是唯一 Markdown 报告输出层与 Telegram 推送来源
- 报告生成后需先落盘到 `reports/`，再发送 Telegram 摘要与附件

### 三、V2 / V4 / 优化层职责边界

- **执行层 / V2 策略池**：当前生产主链；盘后运行 `execute_pipeline_v2`，生成候选并写入 `strategy_picks`
- **执行层 / V4 量价配合**：独立专题链路；使用自身流程执行，日常命中汇总写入 `strategy_picks`
- **优化层 / V2 参数优化**：只优化 V2 trigger，通过全市场回放 `execute_pipeline_v2` 评估，结果写入 `market_optimization_tasks`
- **优化层 / V4 参数优化**：只优化 `volume-price-pattern`，通过独立 `run_backtest` / `run_grid_search` 评估，结果写入 `v4_backtest_results`
- **投研层 / StarMap**：对 V2/V4 当日结果做统一融合，输出增强交易计划与投研报告

### 四、已退场与保留原则

- 旧 `trade_plan` 代码链路已退场；如发现新增逻辑仍写回旧表/旧接口，视为偏离当前架构
- V1 主执行链路与废弃 V1 策略已删除；不要重新接回生产主路径
- 当前允许保留的旧基础策略，仅限被 V2 adapter 复用的能力型策略
- 若后续新增策略链路，优先判断其应归属：执行层、优化层，还是投研层；避免再次出现“多计划层并存”

### 五、文档同步要求

- 只要主链关系、计划落库表、报告出口、策略职责边界发生变化，必须同步更新：
  - `README.md`
  - `CLAUDE.md`
  - `docs/用户指南.md`
  - `docs/数据库表清单.md`
- 若涉及设计口径调整，还必须同步对应设计文档，避免“代码已改、文档仍沿用旧叙事”

## 不做

用户权限、高手跟投、测试机械补全、前端骨架打磨、调度器锦上添花、V2 79 策略补全、设计文档补全。
