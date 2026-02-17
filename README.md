# A 股智能选股系统

面向个人投资者的 A 股智能选股与回测平台。基于多维度策略筛选 + AI 智能分析，帮助发现投资机会。

## 功能特性

- **Tushare 数据源** — 对接 Tushare Pro API，自动同步日线行情、财务指标、资金流向等数据，引入 raw 层作为数据缓冲，解耦数据获取和清洗逻辑；已实施 P0（基础行情 6 张表）、P1（财务数据 10 张表，使用 VIP 接口按季度批量获取）和 P2（资金流向 10 张表）
- **高性能数据同步** — 按日期批量获取全市场数据（避免逐股票遍历），令牌桶限流（400 QPS），全链路性能日志支持瓶颈分析（数据同步、技术指标、缓存刷新、调度任务）
- **智能数据更新** — 每日自动触发数据同步，数据未就绪时智能嗅探重试（每 15 分钟），超时自动报警，无需手动干预；每日自动更新交易日历（获取未来 90 天数据）
- **数据完整性检查** — 基于累积进度表（`stock_sync_progress`）的断点续传机制，启动时自动恢复未完成的同步任务，按 365 天/批分批处理，支持退市股票智能过滤和失败自动重试（每日 20:00），完整性门控确保数据完成率达标后才执行策略
- **数据初始化向导** — 交互式引导首次数据初始化，支持 1年/3年/自定义范围选项
- **优雅关闭** — 捕获 SIGTERM/SIGINT 信号，等待运行中的任务完成后再关闭（30秒超时），启动时自动清除残留同步锁
- **技术指标计算** — 自动计算 MA/MACD/KDJ/RSI/BOLL/ATR 等常用技术指标
- **12 种选股策略** — 8 种技术面策略 + 4 种基本面策略，支持自由组合
- **5 层漏斗筛选** — SQL 粗筛 → 技术面 → 基本面 → 排序 → AI 终审
- **AI 智能分析** — 接入 Gemini Flash，对候选股票进行综合评分和投资建议
- **历史回测** — 基于 Backtrader，支持 A 股佣金、印花税、涨跌停限制
- **定时任务** — 盘后自动执行数据同步、指标计算、缓存刷新、策略筛选全链路
- **Redis 缓存** — 技术指标 Cache-Aside 缓存 + 选股结果缓存，Redis 不可用时自动降级到数据库
- **HTTP API** — RESTful 接口，支持策略执行、回测提交和结果查询
- **前端界面** — React 18 + Ant Design 5 + ECharts，选股工作台 + 回测中心
- **测试覆盖** — 单元测试覆盖全部 API 端点、策略引擎、回测引擎、数据源客户端、数据完整性检查、数据初始化向导、优雅关闭、自动数据更新、P2 资金流向 ETL；集成测试覆盖 P0/P1 数据校验（数据完整性、ETL 转换正确性、数据质量、跨表一致性）

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.12 + FastAPI + SQLAlchemy (async) |
| 数据校验 | Pydantic v2 |
| 数据源 | Tushare Pro API |
| 数据库 | PostgreSQL + asyncpg |
| 缓存 | Redis + hiredis |
| 回测引擎 | Backtrader |
| AI 分析 | Google Gemini Flash (`google-genai`) |
| 定时任务 | APScheduler |
| 包管理 | uv |
| 前端框架 | React 18 + TypeScript |
| UI 组件库 | Ant Design 5 |
| 图表 | ECharts |
| 前端构建 | Vite 6 + pnpm |
| 数据请求 | TanStack React Query + Axios |

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- uv 包管理器
- Node.js 18+ 和 pnpm（前端）

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd stock-selector

# 安装依赖
uv sync

# 复制环境变量配置
cp .env.example .env
# 编辑 .env，填入数据库连接和 Gemini API Key
```

### 配置

编辑 `.env` 文件，必填项：

```bash
# 数据库连接
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/stock_selector

# Tushare API Token（必填）
TUSHARE_TOKEN=your-tushare-token-here

# AI 分析（可选，不填则跳过 AI 评分）
# 方式一：API Key
GEMINI_API_KEY=your-gemini-api-key
# 方式二：Google ADC 认证（Vertex AI，需要 GCP 项目和 Billing）
GEMINI_USE_ADC=true
GEMINI_GCP_PROJECT=your-gcp-project-id   # ADC 模式必填
GEMINI_GCP_LOCATION=us-central1           # ADC 模式，默认 us-central1

# Redis（可选，不配置则缓存功能自动降级）
REDIS_HOST=localhost
REDIS_PORT=6379

# 自动数据更新（可选，默认启用）
AUTO_UPDATE_ENABLED=true                # 是否启用自动数据更新
AUTO_UPDATE_PROBE_INTERVAL=15           # 嗅探间隔（分钟）
AUTO_UPDATE_PROBE_TIMEOUT=18:00         # 嗅探超时时间
AUTO_UPDATE_PROBE_THRESHOLD=0.8         # 嗅探成功阈值（80%样本有数据）
```

完整配置项见 [.env.example](.env.example)。

### 初始化数据库

```bash
# 执行数据库迁移（创建业务表 + raw 层表）
uv run alembic upgrade head
```

### 导入数据

**方式一：使用数据初始化向导（推荐）**

交互式向导会引导您完成首次数据初始化，自动执行股票列表、交易日历、日线数据、技术指标的完整流程：

```bash
uv run python -m scripts.init_data
```

向导提供三种数据范围选项：
- **最近 1 年**：约 250 个交易日，适合快速测试
- **最近 3 年**：约 750 个交易日，推荐日常使用
- **自定义范围**：指定起止日期，超过 5 年会有警告提示

**方式二：手动导入（高级用户）**

```bash
# 同步股票列表
uv run python -m app.data.cli sync-stocks

# 同步日线行情（指定日期范围）
uv run python -m app.data.cli sync-daily --start 2024-01-01 --end 2026-02-07

# 同步复权因子（首次全量导入，约 30-60 分钟）
uv run python -m app.data.cli sync-adj-factor

# 强制刷新所有复权因子（除权除息日后使用）
uv run python -m app.data.cli sync-adj-factor --force

# 计算技术指标
uv run python -m app.data.cli calc-indicators --start 2024-01-01 --end 2026-02-07

# 手动补齐缺失的交易日数据（断点续传）
uv run python -m app.data.cli backfill-daily --start 2024-01-01 --end 2026-02-07

# 限制并发数（避免 API 限流）
uv run python -m app.data.cli backfill-daily --start 2024-01-01 --end 2026-02-07 --rate-limit 5
```

**数据完整性检查：** 服务启动时会自动检测最近 30 天（可配置）的数据完整性，如果发现缺失的交易日会自动补齐。可通过以下配置项控制：

```bash
# .env 配置
DATA_INTEGRITY_CHECK_ENABLED=true   # 启动时是否检查数据完整性
DATA_INTEGRITY_CHECK_DAYS=30        # 检查最近 N 天的数据完整性
```

如需跳过启动时检查，可使用 `--skip-integrity-check` 参数启动服务。

### 启动服务

```bash
uv run uvicorn app.main:app --reload

# 跳过启动时数据完整性检查
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app --reload
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/strategy/run` | 执行选股策略管道（未指定日期时自动使用最近有数据的交易日） |
| GET | `/api/v1/strategy/list` | 获取可用策略列表（支持按分类过滤） |
| GET | `/api/v1/strategy/schema/{name}` | 获取策略参数元数据 |
| POST | `/api/v1/backtest/run` | 执行回测并返回结果 |
| GET | `/api/v1/backtest/result/{task_id}` | 查询回测结果（含交易明细和净值曲线） |
| GET | `/api/v1/backtest/list` | 分页查询回测任务列表 |
| GET | `/api/v1/data/kline/{ts_code}` | 查询股票日 K 线数据 |

### 启动前端

```bash
cd web
pnpm install
pnpm dev
```

前端开发服务器启动在 http://localhost:5173，API 请求自动代理到后端。

## 部署

### 打包项目

使用打包脚本将项目打包为 tarball，便于传输到生产服务器：

```bash
uv run python -m scripts.package
```

打包脚本会：
- 自动获取版本号（git tag 或 commit hash）
- 收集必需文件（app/, scripts/, alembic/, uv.lock, .env.example, README.md 等）
- 排除开发文件（tests/, .git/, __pycache__/, .env 等）
- 验证包内容完整性
- 生成 `dist/stock-selector-<version>.tar.gz`

### 部署到服务器

```bash
# 1. 传输到目标服务器
scp dist/stock-selector-<version>.tar.gz user@server:/path/

# 2. 在服务器上解压
tar -xzf stock-selector-<version>.tar.gz
cd stock-selector

# 3. 安装依赖
uv sync

# 4. 配置环境变量
cp .env.example .env
vim .env  # 填入数据库连接、Redis、Gemini API Key 等

# 5. 初始化数据库
uv run alembic upgrade head

# 6. 初始化数据（使用交互式向导）
uv run python -m scripts.init_data

# 7. 启动服务
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 运维管理

### 服务管理

**启动服务：**

```bash
# 开发模式（自动重载）
uv run uvicorn app.main:app --reload

# 生产模式（指定主机和端口）
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000

# 跳过启动时数据完整性检查
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app
```

**停止服务：**

服务支持优雅关闭，会等待运行中的任务完成后再关闭（30秒超时）。uvicorn 会自动处理 SIGTERM 和 SIGINT 信号：

```bash
# 发送 SIGTERM 信号（推荐）
kill -TERM <pid>

# 或按 Ctrl+C（SIGINT）
```

优雅关闭流程：
1. 停止调度器，等待运行中的任务完成（最多 30 秒）
2. 关闭 BaoStock 连接池
3. 关闭 Redis 连接
4. 关闭数据库连接

**查看日志：**

```bash
# 服务日志输出到 stdout
# 可以使用 systemd 或其他工具管理日志
```

### 数据完整性检查

服务启动时会自动检测最近 N 天（默认 30 天）的数据完整性，如果发现缺失的交易日会自动补齐。

**配置选项：**

```bash
# .env 配置
DATA_INTEGRITY_CHECK_ENABLED=true   # 启动时是否检查数据完整性
DATA_INTEGRITY_CHECK_DAYS=30        # 检查最近 N 天的数据完整性
```

**跳过启动时检查：**

```bash
SKIP_INTEGRITY_CHECK=true uv run uvicorn app.main:app
```

**手动补齐缺失数据：**

```bash
# 补齐指定日期范围的缺失数据
uv run python -m app.data.cli backfill-daily --start 2024-01-01 --end 2026-02-07

# 限制并发数（避免 API 限流）
uv run python -m app.data.cli backfill-daily --start 2024-01-01 --end 2026-02-07 --rate-limit 5
```

### 数据初始化

**首次初始化（推荐使用向导）：**

```bash
uv run python -m scripts.init_data
```

交互式向导提供三种数据范围选项：
- **最近 1 年**：约 250 个交易日，适合快速测试
- **最近 3 年**：约 750 个交易日，推荐日常使用
- **自定义范围**：指定起止日期，超过 5 年会有警告提示

**手动初始化步骤：**

```bash
# 1. 同步股票列表
uv run python -m app.data.cli import-stocks

# 2. 同步交易日历
uv run python -m app.data.cli import-calendar --start 2024-01-01

# 3. 同步日线数据
uv run python -m app.data.cli import-daily --start 2024-01-01

# 4. 同步复权因子
uv run python -m app.data.cli sync-adj-factor

# 5. 计算技术指标
uv run python -m app.data.cli compute-indicators
```

### 日常维护

**每日数据同步：**

服务启动后，定时任务会自动执行每日数据同步（默认周一至周五 15:30）。也可以手动触发：

```bash
uv run python -m app.data.cli sync-daily
```

**更新技术指标：**

```bash
# 增量计算最新交易日的技术指标
uv run python -m app.data.cli update-indicators

# 指定日期
uv run python -m app.data.cli update-indicators --date 2026-02-07
```

**数据库备份：**

```bash
# 使用 PostgreSQL 工具备份
pg_dump -U postgres stock_selector > backup.sql

# 恢复
psql -U postgres stock_selector < backup.sql
```

## 项目结构

```
stock-selector/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理（pydantic-settings）
│   ├── database.py             # SQLAlchemy 异步引擎
│   ├── models/                 # ORM 模型（12 张业务表 + 90 张 raw 层表）
│   ├── data/                   # 数据采集模块
│   │   ├── baostock.py         #   BaoStock 客户端
│   │   ├── akshare.py          #   AKShare 客户端
│   │   ├── pool.py             #   BaoStock 连接池
│   │   ├── batch.py            #   批量日线同步
│   │   ├── adj_factor.py       #   复权因子批量更新
│   │   ├── etl.py              #   ETL 清洗
│   │   ├── indicator.py        #   技术指标计算
│   │   └── manager.py          #   DataManager
│   ├── strategy/               # 策略引擎
│   │   ├── base.py             #   BaseStrategy 抽象基类
│   │   ├── technical/          #   8 种技术面策略
│   │   ├── fundamental/        #   4 种基本面策略
│   │   ├── factory.py          #   策略注册工厂
│   │   └── pipeline.py         #   5 层执行管道
│   ├── ai/                     # AI 分析模块
│   │   ├── clients/gemini.py   #   Gemini Flash 客户端
│   │   ├── prompts.py          #   Prompt 模板
│   │   ├── schemas.py          #   响应校验模型
│   │   └── manager.py          #   AIManager 编排器
│   ├── backtest/               # 回测引擎
│   │   ├── engine.py           #   Cerebro 配置
│   │   ├── strategy.py         #   AStockStrategy 基类
│   │   ├── commission.py       #   A 股佣金模型
│   │   ├── price_limit.py      #   涨跌停检查
│   │   └── writer.py           #   结果写入
│   ├── scheduler/              # 定时任务
│   │   ├── core.py             #   APScheduler 配置
│   │   └── jobs.py             #   任务定义（含缓存刷新步骤）
│   ├── cache/                  # Redis 缓存
│   │   ├── redis_client.py     #   连接管理（init/get/close）
│   │   ├── tech_cache.py       #   技术指标缓存（Cache-Aside）
│   │   └── pipeline_cache.py   #   选股结果缓存
│   └── api/                    # HTTP API
│       ├── strategy.py         #   策略执行 API
│       ├── backtest.py         #   回测 API
│       └── data.py             #   数据查询 API（K 线）
├── web/                        # 前端（React + TypeScript）
│   ├── src/
│   │   ├── api/                #   API 请求函数
│   │   ├── layouts/            #   布局组件
│   │   ├── pages/
│   │   │   ├── workbench/      #   选股工作台
│   │   │   └── backtest/       #   回测中心
│   │   └── types/              #   TypeScript 类型定义
│   └── vite.config.ts          #   Vite 配置（含 API 代理）
├── tests/                      # 测试
│   ├── unit/                   #   单元测试
│   └── integration/            #   集成测试
├── alembic/                    # 数据库迁移
├── docs/                       # 文档
│   ├── design/                 #   设计文档（10 个）
│   │   ├── 00-概要设计-v2.md
│   │   ├── 01-详细设计-数据采集.md
│   │   ├── 02-详细设计-策略引擎.md
│   │   ├── 03-详细设计-AI与回测.md
│   │   ├── 04-详细设计-前端与交互.md
│   │   ├── 10-系统设计-定时任务调度.md
│   │   ├── 11-系统设计-缓存策略.md
│   │   ├── 13-系统设计-测试策略.md
│   │   ├── 99-实施范围-V1与V2划分.md
│   │   └── task-设计补全.md
│   └── 用户指南.md
├── scripts/                    # 工具脚本
│   ├── package.py              #   打包脚本
│   ├── init_data.py            #   数据初始化向导
│   └── verify_*.py             #   验证脚本
├── openspec/                   # OpenSpec 工作流
├── PROJECT_TASKS.md            # 项目任务清单（含 V2 详细计划）
└── README.md                   # 本文件
```

## 设计文档

详细的系统设计文档位于 `docs/design/` 目录：

- **00-概要设计-v2.md** - 系统总体架构、模块划分、数据模型
- **01-详细设计-数据采集.md** - 多源数据采集、ETL、智能数据自动更新系统
- **02-详细设计-策略引擎.md** - 79 种策略、Pipeline 架构、策略注册
- **03-详细设计-AI与回测.md** - AI 三模型、Backtrader 回测、涨跌停
- **04-详细设计-前端与交互.md** - 页面交互、路由、API 契约、状态管理
- **10-系统设计-定时任务调度.md** - 每日任务编排、APScheduler、智能数据自动更新
- **11-系统设计-缓存策略.md** - Redis 缓存设计
- **13-系统设计-测试策略.md** - 测试分层、Mock、核心用例
- **99-实施范围-V1与V2划分.md** - ⚠️ 关键：V1/V2 范围划分，V1 已实施功能，V2 计划功能
- **task-设计补全.md** - 任务跟踪

**V2 详细实施计划见：** [PROJECT_TASKS.md](PROJECT_TASKS.md)

