# A 股智能选股系统

面向个人投资者的 A 股智能选股与回测平台。基于多维度策略筛选 + AI 智能分析，帮助发现投资机会。

## 功能特性

- **多源数据采集** — 对接 BaoStock + AKShare，自动同步日线行情、财务指标、资金流向等数据，批量写入自动适配 asyncpg 参数限制
- **高性能数据同步** — BaoStock 连接池 + 批量并发同步，8000+ 只股票日线数据同步从 2-3 小时降至 15-30 分钟（4-8 倍提升），详细性能日志支持瓶颈分析
- **技术指标计算** — 自动计算 MA/MACD/KDJ/RSI/BOLL/ATR 等常用技术指标
- **12 种选股策略** — 8 种技术面策略 + 4 种基本面策略，支持自由组合
- **5 层漏斗筛选** — SQL 粗筛 → 技术面 → 基本面 → 排序 → AI 终审
- **AI 智能分析** — 接入 Gemini Flash，对候选股票进行综合评分和投资建议
- **历史回测** — 基于 Backtrader，支持 A 股佣金、印花税、涨跌停限制
- **定时任务** — 盘后自动执行数据同步、指标计算、缓存刷新、策略筛选全链路
- **Redis 缓存** — 技术指标 Cache-Aside 缓存 + 选股结果缓存，Redis 不可用时自动降级到数据库
- **HTTP API** — RESTful 接口，支持策略执行、回测提交和结果查询
- **前端界面** — React 18 + Ant Design 5 + ECharts，选股工作台 + 回测中心
- **测试覆盖** — 354 个单元测试用例，覆盖全部 API 端点、策略引擎、回测引擎、数据源客户端

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.12 + FastAPI + SQLAlchemy (async) |
| 数据校验 | Pydantic v2 |
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
```

完整配置项见 [.env.example](.env.example)。

### 初始化数据库

```bash
# 执行数据库迁移（创建 12 张表）
uv run alembic upgrade head
```

### 导入数据

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
```

### 启动服务

```bash
uv run uvicorn app.main:app --reload
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/strategy/run` | 执行选股策略管道 |
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

## 项目结构

```
stock-selector/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── config.py               # 配置管理（pydantic-settings）
│   ├── database.py             # SQLAlchemy 异步引擎
│   ├── models/                 # ORM 模型（12 张表）
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
└── openspec/                   # OpenSpec 工作流
```
