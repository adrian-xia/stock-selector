# A股智能选股系统 - 项目指南

## 语言要求
对话全程中文

## 项目概述

面向个人投资者的 A 股智能选股与回测平台。单机部署、单人使用。

## 设计文档

所有设计文档位于独立目录，**不在代码仓库内**：

```
~/Developer/Design/stock-selector-design/
├── 00-概要设计-v2.md              # 系统总体架构、模块划分、数据模型
├── 01-详细设计-数据采集.md         # 多源数据采集、ETL、标准层 DDL
├── 02-详细设计-策略引擎.md         # 79 种策略、Pipeline 架构、策略注册
├── 03-详细设计-AI与回测.md         # AI 三模型、Backtrader 回测、涨跌停
├── 04-详细设计-前端与交互.md       # 页面交互、路由、API 契约、状态管理
├── 10-系统设计-定时任务调度.md     # 每日任务编排、APScheduler
├── 11-系统设计-缓存策略.md         # Redis 缓存设计
├── 13-系统设计-测试策略.md         # 测试分层、Mock、核心用例
├── 99-实施范围-V1与V2划分.md       # ⚠️ 关键：V1/V2 范围划分
└── task-设计补全.md                # 任务跟踪
```

**编码前必读 `99-实施范围-V1与V2划分.md`**，它标注了每个章节是 V1 必须、V1 简化还是 V2 再加。

## V1 范围（当前阶段）

- 数据采集：BaoStock + AKShare，直接入标准表，无 raw 中转层
- 策略引擎：10-15 种核心策略，扁平继承，单模式接口
- AI 分析：仅 Gemini Flash 单模型，无降级链路
- 回测：Backtrader 同步执行，无 Redis 队列
- 前端：选股工作台 + 回测结果页，轮询（无 WebSocket）
- 数据库：12 张表（见 99-实施范围 §八）
- 不做：用户权限、实时监控、新闻舆情、高手跟投

## 技术栈

- **后端：** Python 3.12 + FastAPI + SQLAlchemy + Pydantic
- **回测：** Backtrader
- **数据库：** PostgreSQL（普通表，不用 TimescaleDB）
- **缓存：** Redis（仅缓存技术指标）
- **AI：** Gemini Flash（V1 单模型）
- **前端：** React 18 + TypeScript + Ant Design 5 + ECharts
- **包管理：** uv
- **部署：** 直接运行（uvicorn），不用 Docker/Nginx

## 编码规范

- Python 3.12+ 语法，所有函数必须有类型注解
- async/await 用于 IO 操作（数据库、API 调用）
- 使用 Pydantic v2 做数据校验
- SQL 全部使用参数化查询，禁止字符串拼接
- 日志使用 Python logging，不用 print
- 配置项写 `.env` 文件，通过 pydantic-settings 加载
- 所有代码需要详细的中文注释

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
│   │   ├── sources/          # BaoStock / AKShare 客户端
│   │   ├── etl.py            # ETL 清洗
│   │   └── manager.py        # DataManager
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
│   │   └── tech_cache.py     # 技术指标缓存
│   ├── scheduler/            # 定时任务
│   │   └── jobs.py           # APScheduler 任务
│   └── api/                  # HTTP API
│       ├── strategy.py       # 策略 API
│       ├── backtest.py       # 回测 API
│       └── data.py           # 数据查询 API
├── web/                      # 前端（React）
├── tests/
│   ├── fixtures/             # 测试数据
│   ├── unit/                 # 单元测试
│   ├── integration/          # 集成测试
│   └── api/                  # API 测试
└── scripts/                  # 工具脚本
    └── record_fixtures.py    # 录制测试数据
```
