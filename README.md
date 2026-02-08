# A 股智能选股系统

面向个人投资者的 A 股智能选股与回测平台。基于多维度策略筛选 + AI 智能分析，帮助发现投资机会。

## 功能特性

- **多源数据采集** — 对接 BaoStock + AKShare，自动同步日线行情、财务指标、资金流向等数据
- **技术指标计算** — 自动计算 MA/MACD/KDJ/RSI/BOLL/ATR 等常用技术指标
- **12 种选股策略** — 8 种技术面策略 + 4 种基本面策略，支持自由组合
- **5 层漏斗筛选** — SQL 粗筛 → 技术面 → 基本面 → 排序 → AI 终审
- **AI 智能分析** — 接入 Gemini Flash，对候选股票进行综合评分和投资建议
- **历史回测** — 基于 Backtrader，支持 A 股佣金、印花税、涨跌停限制
- **定时任务** — 盘后自动执行数据同步、指标计算、策略筛选全链路
- **HTTP API** — RESTful 接口，支持策略执行、回测提交和结果查询

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | Python 3.12 + FastAPI + SQLAlchemy (async) |
| 数据校验 | Pydantic v2 |
| 数据库 | PostgreSQL + asyncpg |
| 回测引擎 | Backtrader |
| AI 分析 | Google Gemini Flash (`google-genai`) |
| 定时任务 | APScheduler |
| 包管理 | uv |

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL 14+
- uv 包管理器

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
GEMINI_API_KEY=your-gemini-api-key
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

# 计算技术指标
uv run python -m app.data.cli calc-indicators --start 2024-01-01 --end 2026-02-07
```

### 启动服务

```bash
uv run uvicorn app.main:app --reload
```

服务启动后访问 http://localhost:8000/docs 查看 API 文档。

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
│   │   └── jobs.py             #   任务定义
│   └── api/                    # HTTP API
│       ├── strategy.py         #   策略执行 API
│       └── backtest.py         #   回测 API
├── tests/                      # 测试（224 个用例）
│   ├── unit/                   #   单元测试
│   └── integration/            #   集成测试
├── alembic/                    # 数据库迁移
└── openspec/                   # OpenSpec 工作流
```
