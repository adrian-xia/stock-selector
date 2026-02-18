## Context

系统已有完整的 AI 分析能力（Gemini Flash + AIManager），盘后链路（6 个主步骤 + 3 个可选步骤），以及成熟的数据采集模式（TushareClient 令牌桶限流 + 异步包装）。当前缺乏新闻舆情数据输入，投资决策仅依赖技术面和基本面。

现有基础设施：
- `AIManager` — 延迟初始化 GeminiClient，每日调用上限，Token 用量记录
- `GeminiClient.chat_json()` — 异步调用 Gemini，返回 JSON
- `app/scheduler/jobs.py` — 盘后链路，可在步骤 3.9 插入新任务
- `app/config.py` — pydantic-settings 配置管理
- 前端：React 18 + Ant Design 5 + ECharts，3 个页面（workbench/backtest/optimization）

## Goals / Non-Goals

**Goals:**
- G1: 采集东方财富公告数据（上市公司公告标题和摘要）
- G2: 采集淘股吧和雪球的个股讨论热度数据
- G3: 使用 Gemini Flash 对新闻内容进行情感分析（-1 到 +1 评分）
- G4: 持久化新闻和情感数据到数据库
- G5: 提供 HTTP API 查询新闻列表、情感趋势
- G6: 前端新闻仪表盘页面展示新闻和情感趋势
- G7: 集成到盘后链路，每日自动采集和分析

**Non-Goals:**
- 不做实时新闻推送（WebSocket，V4 考虑）
- 不做全文存储（仅存储标题、摘要和情感分析结果，合规考虑）
- 不做自然语言搜索（关键词搜索即可）
- 不做多语言支持（仅中文）
- 不做新闻来源的自动发现（固定 3 个数据源）

## Decisions

### D1: 数据源选择 — 3 个公开数据源

| 数据源 | 数据类型 | 采集方式 |
|--------|---------|---------|
| 东方财富 | 上市公司公告 | HTTP API（公开接口） |
| 淘股吧 | 个股讨论热度 | HTTP 页面解析 |
| 雪球 | 个股讨论热度 | HTTP API |

**理由：** 这 3 个是 A 股投资者最常用的信息源，数据公开可获取。遵守 Robots 协议，不存储原文，仅提取标题和摘要。

### D2: 数据采集架构 — 独立爬虫模块

新建 `app/data/sources/` 目录，每个数据源一个文件：
- `eastmoney.py` — 东方财富公告采集
- `taoguba.py` — 淘股吧热度采集
- `xueqiu.py` — 雪球热度采集

使用 `httpx` 异步 HTTP 客户端（项目已有 aiohttp 但 httpx 更现代），带限流和重试。

**备选方案：** 统一爬虫框架（Scrapy）。
**选择理由：** 只有 3 个简单数据源，独立文件更轻量，无需引入重框架。

### D3: 情感分析 — 复用 Gemini Flash

新建 `app/ai/news_analyzer.py`，复用 `GeminiClient.chat_json()`。Prompt 模板 `news_sentiment_v1.yaml` 定义输入格式和输出 schema。

情感评分：-1（极度负面）到 +1（极度正面），0 为中性。
分类标签：利好、利空、中性、重大事件。

**理由：** 复用现有 AI 基础设施，无需引入新的 NLP 库。Gemini Flash 对中文新闻理解能力足够。

### D4: 数据库表设计

**announcements 表：**
- id, ts_code, title, summary, source (eastmoney/taoguba/xueqiu)
- pub_date (发布日期), url
- sentiment_score (float, -1 到 +1), sentiment_label (str)
- created_at

**sentiment_daily 表（每日聚合）：**
- id, ts_code, trade_date
- avg_sentiment (float), news_count (int)
- positive_count, negative_count, neutral_count
- source_breakdown (JSONB)
- created_at

**理由：** announcements 存储原始新闻条目，sentiment_daily 存储每日聚合指标，前端查询聚合表更高效。

### D5: 盘后链路集成 — 步骤 3.9

在现有盘后链路中插入步骤 3.9（在策略管道之前），流程：
1. 采集当日新闻（3 个数据源并行）
2. 批量情感分析（每批 10 条新闻）
3. 聚合写入 sentiment_daily

失败不阻断后续链路（与其他可选步骤一致）。

### D6: 前端页面 — 新闻仪表盘

新增 `/news` 路由，包含：
- 新闻列表（按日期筛选，支持按股票代码搜索）
- 情感趋势图（ECharts 折线图，展示近 30 天情感走势）
- 个股舆情卡片（选择股票后展示相关新闻和情感评分）

### D7: 配置项

新增配置：
- `news_crawl_enabled: bool = True` — 是否启用新闻采集
- `news_crawl_timeout: int = 30` — 单次采集超时（秒）
- `news_crawl_max_pages: int = 5` — 每个数据源最大采集页数
- `news_sentiment_batch_size: int = 10` — 情感分析批次大小

## Risks / Trade-offs

- [数据源反爬虫] → 使用合理的请求间隔（1-2 秒），设置 User-Agent，遵守 Robots 协议；单个数据源失败不影响其他
- [Gemini API 调用量增加] → 新闻情感分析共享 ai_daily_call_limit 配额；批量分析减少调用次数
- [数据源接口变更] → 每个数据源独立模块，变更时只需修改对应文件；采集失败有日志告警
- [新闻数据量大] → 只采集当日新闻，不做历史回填；announcements 表按日期索引
