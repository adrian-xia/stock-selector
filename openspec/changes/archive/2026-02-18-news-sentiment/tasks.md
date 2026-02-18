## 1. 数据库模型与迁移

- [x] 1.1 创建 `app/models/news.py`，定义 `Announcement` 和 `SentimentDaily` 两个 SQLAlchemy 模型
- [x] 1.2 创建 Alembic 迁移文件，生成 `announcements` 和 `sentiment_daily` 两张表

## 2. 配置项

- [x] 2.1 在 `app/config.py` 新增新闻采集配置项（news_crawl_enabled、news_crawl_timeout、news_crawl_max_pages、news_sentiment_batch_size）
- [x] 2.2 更新 `.env.example` 添加新配置项

## 3. 新闻数据采集

- [x] 3.1 创建 `app/data/sources/__init__.py`
- [x] 3.2 创建 `app/data/sources/eastmoney.py`，实现 `EastMoneyCrawler`（东方财富公告采集）
- [x] 3.3 创建 `app/data/sources/taoguba.py`，实现 `TaogubaCrawler`（淘股吧热度采集）
- [x] 3.4 创建 `app/data/sources/xueqiu.py`，实现 `XueqiuCrawler`（雪球热度采集）
- [x] 3.5 创建 `app/data/sources/fetcher.py`，实现 `fetch_all_news()` 统一采集入口（并行调用 3 个爬虫）

## 4. AI 情感分析

- [x] 4.1 创建 `app/ai/prompts/news_sentiment_v1.yaml`，定义情感分析 Prompt 模板
- [x] 4.2 创建 `app/ai/news_analyzer.py`，实现 `NewsSentimentAnalyzer`（批量情感分析 + 每日聚合）

## 5. 新闻 API

- [x] 5.1 创建 `app/api/news.py`，定义 Pydantic 请求/响应模型
- [x] 5.2 实现 `GET /api/v1/news/list` 端点（分页 + 筛选）
- [x] 5.3 实现 `GET /api/v1/news/sentiment-trend/{ts_code}` 端点
- [x] 5.4 实现 `GET /api/v1/news/sentiment-summary` 端点
- [x] 5.5 在 `app/main.py` 注册 news_router

## 6. 盘后链路集成

- [x] 6.1 在 `app/scheduler/jobs.py` 新增步骤 3.9：新闻采集与情感分析（受 news_crawl_enabled 控制，失败不阻断）

## 7. 前端页面

- [x] 7.1 创建 `web/src/api/news.ts`，封装新闻相关 API 请求函数
- [x] 7.2 创建 `web/src/types/news.ts`，定义 TypeScript 类型
- [x] 7.3 创建 `web/src/pages/news/index.tsx`，实现新闻仪表盘页面（新闻列表 + 情感趋势图 + 每日摘要）
- [x] 7.4 更新 `web/src/App.tsx` 添加 `/news` 路由
- [x] 7.5 更新侧边栏导航菜单，新增"新闻舆情"入口

## 8. 单元测试

- [x] 8.1 创建 `tests/unit/test_news_crawler.py`，测试 3 个爬虫（mock HTTP）
- [x] 8.2 创建 `tests/unit/test_news_analyzer.py`，测试情感分析和每日聚合（mock Gemini）
- [x] 8.3 创建 `tests/unit/test_news_api.py`，测试 API 端点

## 9. 文档更新

- [x] 9.1 更新 `docs/design/00-概要设计-v2.md` 模块8 新闻舆情部分，标注为已实施
- [x] 9.2 更新 `docs/design/99-实施范围-V1与V2划分.md`
- [x] 9.3 更新 `README.md`，新增新闻舆情功能说明
- [x] 9.4 更新 `CLAUDE.md`，新增新闻舆情模块到目录结构
- [x] 9.5 更新 `PROJECT_TASKS.md`，标记 Change 10 为已完成
