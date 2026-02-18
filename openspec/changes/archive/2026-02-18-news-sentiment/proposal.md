## Why

系统已有 AI 智能分析能力（Gemini Flash），但缺乏新闻舆情数据输入。投资决策不仅依赖技术面和基本面，还需要关注市场情绪和新闻事件。新闻舆情监控模块通过采集公告和舆情数据，结合 AI 情感分析，为用户提供更全面的投资参考。

## What Changes

- 新增新闻数据采集：东方财富公告、淘股吧情绪、雪球讨论（HTTP 爬虫，遵守 Robots 协议）
- 新增 AI 情感分析：复用 Gemini Flash，对新闻内容进行情感打分（-1 到 +1）和分类
- 新增数据库表：`announcements`（公告）、`sentiment_data`（情感分析结果）
- 新增 API 端点：查询新闻列表、情感趋势、个股舆情
- 新增前端新闻仪表盘页面：新闻列表、情感趋势图、个股关联
- 盘后链路集成：每日自动采集新闻并执行情感分析（失败不阻断后续链路）
- 新增 Prompt 模板：`news_sentiment_v1.yaml`

## Capabilities

### New Capabilities
- `news-data-source`: 新闻数据采集层（东方财富公告、淘股吧、雪球爬虫），含限流和重试
- `news-sentiment-analysis`: AI 情感分析引擎，复用 Gemini Flash 对新闻进行情感打分和分类
- `news-sentiment-models`: 新闻和情感分析数据库模型（announcements、sentiment_data）+ Alembic 迁移
- `news-sentiment-api`: 新闻舆情 HTTP API（新闻列表、情感趋势、个股舆情查询）
- `news-sentiment-frontend`: 前端新闻仪表盘页面（新闻列表、情感趋势图、个股关联）
- `news-sentiment-scheduler`: 盘后链路集成，每日自动采集和分析

### Modified Capabilities
_(无需修改现有 spec)_

## Impact

- 新增模块：`app/data/sources/`（新闻爬虫）
- 新增：`app/ai/prompts/news_sentiment_v1.yaml`（情感分析 Prompt）
- 新增：`app/ai/news_analyzer.py`（新闻情感分析器）
- 新增 API：`app/api/news.py`（`/api/v1/news/*`）
- 新增模型：`app/models/news.py`（2 张表）
- 新增前端页面：`web/src/pages/news/`
- 修改：`app/scheduler/jobs.py`（新增步骤 3.9）
- 修改：`app/main.py`（注册新路由）
- 修改：`app/config.py`（新增新闻采集配置项）
- 修改：`web/src/`（路由、导航菜单）
- 依赖：复用现有 AIManager / GeminiClient
- 新增 Alembic 迁移文件
- 新增 Python 依赖：`httpx`（异步 HTTP 客户端）或复用 `aiohttp`
