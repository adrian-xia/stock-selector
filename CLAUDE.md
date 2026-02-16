# A股智能选股系统 - 项目指南

## 语言要求
对话全程中文

## 项目概述

面向个人投资者的 A 股智能选股与回测平台。单机部署、单人使用。

## 设计文档

设计文档已复制到项目中，位于 `docs/design/` 目录：

```
docs/design/
├── 00-概要设计-v2.md              # 系统总体架构、模块划分、数据模型
├── 01-详细设计-数据采集.md         # 多源数据采集、ETL、智能数据自动更新系统
├── 02-详细设计-策略引擎.md         # 79 种策略、Pipeline 架构、策略注册
├── 03-详细设计-AI与回测.md         # AI 三模型、Backtrader 回测、涨跌停
├── 04-详细设计-前端与交互.md       # 页面交互、路由、API 契约、状态管理
├── 10-系统设计-定时任务调度.md     # 每日任务编排、APScheduler、智能数据自动更新
├── 11-系统设计-缓存策略.md         # Redis 缓存设计
├── 13-系统设计-测试策略.md         # 测试分层、Mock、核心用例
├── 99-实施范围-V1与V2划分.md       # ⚠️ 关键：V1/V2 范围划分，V1 已实施功能，V2 计划功能
└── task-设计补全.md                # 任务跟踪
```

**编码前必读 `docs/design/99-实施范围-V1与V2划分.md`**，它标注了每个章节是 V1 必须、V1 简化、V1 已实施还是 V2 再加。

**V2 详细实施计划见：** `PROJECT_TASKS.md` 中的"V2 详细实施计划"章节。

**设计文档源仓库：** `~/Developer/Design/stock-selector-design/`（独立 Git 仓库，已推送到 GitHub）


## V1 范围（当前阶段）

- 数据采集：Tushare Pro API，引入 raw 层作为数据缓冲（原始表），解耦数据获取和清洗逻辑，按日期批量获取全市场数据
- 性能优化：令牌桶限流（400 QPS），全链路性能日志支持瓶颈分析
- 自动数据更新：每日自动触发数据同步，数据未就绪时智能嗅探重试（每 15 分钟），超时自动报警（V1 记录日志，V2 接入企业微信/钉钉），基于 Redis 的任务状态管理；每日自动更新交易日历（获取未来 90 天数据，周末任务作为兜底）
- 数据完整性：基于累积进度表（`stock_sync_progress`）的断点续传，启动时自动恢复未完成同步，按 365 天/批分批处理数据和指标，退市智能过滤，失败自动重试（每日 20:00），完整性门控（完成率 >= 95% 才执行策略），Redis 分布式锁防并发，环境隔离（APP_ENV_FILE）
- 数据初始化：交互式向导引导首次数据初始化，支持 1年/3年/自定义范围选项，自动执行完整流程（股票列表 → 交易日历 → 日线数据 → 技术指标）
- 优雅关闭：利用 uvicorn 内置信号处理机制，在 lifespan shutdown 阶段等待运行中的任务完成后再关闭（30秒超时），启动时自动清除残留同步锁，完整的关闭日志记录
- 打包部署：提供打包脚本生成 tarball，自动收集必需文件并排除开发文件，支持版本号管理（git tag / commit hash）
- 策略引擎：12 种核心策略（8 种技术面 + 4 种基本面），扁平继承，单模式接口
- AI 分析：❌ V1 未实施（盘后链路不包含 AI 分析步骤），V2 再接入 Gemini Flash 单模型
- 回测：✅ V1 已实施，Backtrader 同步执行，无 Redis 队列
- 前端：选股工作台 + 回测结果页，轮询（无 WebSocket）
- 数据库：业务表 12 张 + raw 层表 16 张（P0 基础行情 6 张 + P1 财务数据 10 张，P2 资金流向 10 张模型已定义但表未创建）
- 不做：用户权限、实时监控、新闻舆情、高手跟投

## 技术栈

- **后端：** Python 3.12 + FastAPI + SQLAlchemy + Pydantic
- **数据源：** Tushare Pro API（令牌桶限流 400 QPS）
- **回测：** Backtrader
- **数据库：** PostgreSQL（普通表，不用 TimescaleDB）
- **缓存：** Redis（缓存技术指标 + 选股结果，redis[hiredis]）
- **性能优化：** 按日期批量获取全市场数据 + 全链路性能日志（连接池、API、清洗、入库、指标计算、缓存刷新、调度任务分步计时）
- **自动更新：** 数据嗅探 + 智能重试 + 任务状态管理（Redis）+ 通知报警（V1 日志，V2 企业微信/钉钉）+ 交易日历自动更新（每日获取未来 90 天数据）
- **AI：** Gemini Flash（V1 单模型，支持 API Key 和 ADC/Vertex AI 两种认证）
- **前端：** React 18 + TypeScript + Ant Design 5 + ECharts
- **前端构建：** Vite 6 + pnpm
- **前端数据层：** TanStack React Query + Axios + Zustand
- **包管理：** uv（后端）、pnpm（前端）
- **部署：** 直接运行（uvicorn），不用 Docker/Nginx

## 编码规范

- Python 3.12+ 语法，所有函数必须有类型注解
- async/await 用于 IO 操作（数据库、API 调用）
- 使用 Pydantic v2 做数据校验
- SQL 全部使用参数化查询，禁止字符串拼接
- 日志使用 Python logging，不用 print
- 配置项写 `.env` 文件，通过 pydantic-settings 加载
- 所有代码需要详细的中文注释
- **每次完成一个模块或功能变更，必须同步更新以下文件（不可遗漏）：**
  - `README.md` — 功能特性、技术栈、环境要求、配置说明、项目结构、测试数量
  - `CLAUDE.md` — 技术栈、V1 范围、目录结构
  - 如果新增了依赖，还需更新 `.env.example`

## 提交前强制检查清单

**⚠️ 重要：每次 Git 提交前必须完成以下检查，如有不一致则拒绝提交！**

### 1. 设计文档一致性检查

在提交代码前，必须检查实现是否与设计文档一致：

#### 检查步骤：

1. **确认变更范围**
   - 本次变更涉及哪些模块？（数据采集/策略引擎/回测/AI/定时任务/前端）
   - 是 V1 功能还是 V2 功能？

2. **查阅相关设计文档**
   - 数据采集 → `docs/design/01-详细设计-数据采集.md`
   - 策略引擎 → `docs/design/02-详细设计-策略引擎.md`
   - AI 与回测 → `docs/design/03-详细设计-AI与回测.md`
   - 前端交互 → `docs/design/04-详细设计-前端与交互.md`
   - 定时任务 → `docs/design/10-系统设计-定时任务调度.md`
   - 缓存策略 → `docs/design/11-系统设计-缓存策略.md`
   - V1/V2 范围 → `docs/design/99-实施范围-V1与V2划分.md`

3. **对比实现与设计**
   - ✅ 实现的功能是否在设计文档中有明确说明？
   - ✅ 实现的技术方案是否与设计文档一致？
   - ✅ 数据库表结构是否与设计文档一致？
   - ✅ API 接口是否与设计文档一致？
   - ✅ 配置项是否与设计文档一致？

4. **处理不一致情况**
   - **情况 A：实现符合设计** → 可以提交
   - **情况 B：实现优化了设计** → 先更新设计文档，再提交代码
   - **情况 C：实现偏离了设计** → 拒绝提交，重新实现或修改设计文档

#### 特殊情况处理：

- **V1 简化实施**：如果实现是 V1 简化方案，需在 `99-实施范围-V1与V2划分.md` 中标注为"✅ V1 已实施"
- **V2 功能提前实施**：如果提前实施了 V2 功能，需更新 `99-实施范围-V1与V2划分.md` 和 `PROJECT_TASKS.md`
- **新增功能**：如果是设计文档中未提及的新功能，需先补充设计文档

### 2. 文档同步检查

确认以下文档已同步更新：

- [ ] `README.md` - 功能特性、技术栈、测试数量是否更新？
- [ ] `CLAUDE.md` - V1 范围、技术栈、目录结构是否更新？
- [ ] `.env.example` - 新增配置项是否添加？
- [ ] `docs/design/` - 相关设计文档是否更新？
- [ ] `PROJECT_TASKS.md` - V2 计划是否需要调整？

### 3. 提交信息检查

- [ ] Commit message 是否清晰描述了变更内容？
- [ ] 是否包含 `Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>`？
- [ ] 是否说明了与设计文档的关系（符合设计/优化设计/新增功能）？

### 4. 拒绝提交的情况

以下情况必须拒绝提交，直到问题解决：

- ❌ 实现与设计文档明显不一致，且未更新设计文档
- ❌ V1 实施了 V2 功能，但未更新 `99-实施范围-V1与V2划分.md`
- ❌ 新增了数据库表/字段，但设计文档中未说明
- ❌ 新增了 API 接口，但设计文档中未说明
- ❌ 修改了核心架构，但设计文档未同步更新
- ❌ README.md 或 CLAUDE.md 未同步更新

### 5. 检查示例

**示例 1：实现智能数据自动更新系统**

1. 查阅 `docs/design/10-系统设计-定时任务调度.md` §3.4.1
2. 确认实现包含：数据嗅探、智能重试、Redis 状态管理、超时告警
3. 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注为"✅ V1 已实施"
4. 更新 `README.md` 和 `CLAUDE.md`，说明新功能
5. ✅ 可以提交

**示例 2：提前实施 AI 分析功能**

1. 查阅 `docs/design/03-详细设计-AI与回测.md` §1
2. 发现设计文档标注为"V2 再加"
3. 更新 `docs/design/99-实施范围-V1与V2划分.md`，改为"✅ V1 已实施"
4. 更新 `PROJECT_TASKS.md`，从 V2 计划中移除
5. 更新 `README.md` 和 `CLAUDE.md`
6. ✅ 可以提交

**示例 3：实现了设计文档中没有的功能**

1. 发现实现的功能在设计文档中完全没有提及
2. ❌ 拒绝提交
3. 先补充设计文档（在相应的详细设计文档中添加章节）
4. 更新 `99-实施范围-V1与V2划分.md`
5. 然后再提交代码

---

## OpenSpec 工作流

本项目使用 OpenSpec 管理开发流程：

```
openspec/
├── changes/         # 当前进行中的变更
│   └── archive/     # 已完成的变更归档
└── specs/           # 系统规范文件
```

**开发新功能的流程：**
1. `/opsx:new <feature-name>` — 创建变更
2. `/opsx:ff` — 生成 proposal → specs → design → tasks
3. `/opsx:apply` — 按 tasks 逐步实现
4. `/opsx:archive` — 归档完成的变更

## 部署和运维

### 打包部署

```bash
# 1. 打包项目
uv run python -m scripts.package
# 输出：dist/stock-selector-<version>.tar.gz

# 2. 传输到服务器
scp dist/stock-selector-<version>.tar.gz user@server:/path/

# 3. 在服务器上解压并部署
tar -xzf stock-selector-<version>.tar.gz
cd stock-selector
uv sync
cp .env.example .env && vim .env
uv run alembic upgrade head
uv run python -m scripts.init_data
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### 服务管理

```bash
# 启动服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 跳过启动时数据完整性检查
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app

# 优雅关闭（等待任务完成，30秒超时）
kill -TERM <pid>  # 或按 Ctrl+C
```

### 数据管理

```bash
# 数据初始化向导（首次部署）
uv run python -m scripts.init_data

# 手动补齐缺失数据（断点续传）
uv run python -m app.data.cli backfill-daily --start 2024-01-01 --end 2026-02-07

# 每日数据同步（自动或手动）
uv run python -m app.data.cli sync-daily

# 更新技术指标
uv run python -m app.data.cli update-indicators
```

### 配置项

关键环境变量（.env）：
- `DATABASE_URL` — PostgreSQL 连接字符串
- `TUSHARE_TOKEN` — Tushare Pro API Token（必填）
- `REDIS_HOST` / `REDIS_PORT` — Redis 连接（可选，不配置则缓存降级）
- `GEMINI_API_KEY` — Gemini API Key（可选，不配置则跳过 AI 分析）
- `DATA_INTEGRITY_CHECK_ENABLED` — 启动时是否检查数据完整性（默认 true）
- `DATA_INTEGRITY_CHECK_DAYS` — 检查最近 N 天（默认 30）
- `SKIP_INTEGRITY_CHECK` — 环境变量，跳过启动时检查
- `AUTO_UPDATE_ENABLED` — 是否启用自动数据更新（默认 true）
- `AUTO_UPDATE_PROBE_INTERVAL` — 嗅探间隔（默认 15 分钟）
- `AUTO_UPDATE_PROBE_TIMEOUT` — 嗅探超时时间（默认 18:00）

## 目录结构（规划）

```
stock-selector/
├── CLAUDE.md
├── pyproject.toml
├── .env.example
├── openspec/
├── app/
│   ├── main.py              # FastAPI 入口
│   ├── config.py             # 配置加载
│   ├── logger.py             # 日志配置
│   ├── data/                 # 数据采集模块
│   │   ├── tushare.py        # TushareClient（令牌桶限流 + 异步包装）
│   │   ├── batch.py          # 批量日线同步（按日期批量模式）
│   │   ├── probe.py          # 数据嗅探（检测数据是否就绪）
│   │   ├── etl.py            # ETL 清洗（transform_tushare_*）
│   │   ├── cli.py            # 数据管理 CLI（含 backfill-daily 断点续传命令）
│   │   └── manager.py        # DataManager（sync_raw_daily + etl_daily）
│   ├── strategy/             # 策略引擎
│   │   ├── base.py           # BaseStrategy
│   │   ├── technical/        # 技术面策略
│   │   ├── fundamental/      # 基本面策略
│   │   ├── pipeline.py       # 执行管道
│   │   └── factory.py        # 策略注册
│   ├── backtest/             # 回测引擎
│   │   ├── engine.py         # Cerebro 配置
│   │   ├── strategy.py       # AStockStrategy 基类
│   │   ├── price_limit.py    # 涨跌停检查
│   │   └── writer.py         # 结果写入
│   ├── ai/                   # AI 分析
│   │   ├── clients/          # Gemini 客户端
│   │   └── manager.py        # AIManager
│   ├── cache/                # Redis 缓存
│   │   ├── redis_client.py   # 连接管理（init/get/close）
│   │   ├── tech_cache.py     # 技术指标缓存（Cache-Aside）
│   │   └── pipeline_cache.py # 选股结果缓存
│   ├── scheduler/            # 定时任务
│   │   ├── core.py           # APScheduler 配置（含启动时数据完整性检查）
│   │   ├── state.py          # 任务状态管理（基于 Redis）
│   │   ├── auto_update.py    # 自动数据更新任务
│   │   └── jobs.py           # APScheduler 任务
│   ├── notification/         # 通知报警模块
│   │   └── __init__.py       # NotificationManager（V1 日志，V2 企业微信/钉钉）
│   └── api/                  # HTTP API
│       ├── strategy.py       # 策略 API（未指定日期时自动使用最近有数据的交易日）
│       ├── backtest.py       # 回测 API
│       └── data.py           # 数据查询 API
├── web/                      # 前端（React + TypeScript）
│   ├── src/
│   │   ├── api/              # API 请求函数（Axios）
│   │   ├── layouts/          # 布局组件（AppLayout + Sider）
│   │   ├── pages/
│   │   │   ├── workbench/    # 选股工作台页面
│   │   │   └── backtest/     # 回测中心页面
│   │   └── types/            # TypeScript 类型定义
│   └── vite.config.ts        # Vite 配置（含 /api 代理）
├── tests/
│   ├── fixtures/             # 测试数据
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   └── api/                  # API 测试
└── scripts/                  # 工具脚本
    ├── record_fixtures.py    # 录制测试数据
    ├── test_data_integrity.py # 数据完整性检查测试
    ├── test_graceful_shutdown.py # 优雅关闭功能测试
    └── init_data.py          # 数据初始化向导
```
