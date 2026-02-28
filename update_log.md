# 更新日志

## 2026-02-28：Telegram 通知完整化 — 摘要 + Markdown 文件报告

### 设计思路

系统 4 个定时任务中，仅盘后链路有 Telegram 纯文本通知（受 4096 字符限制经常截断），全市场优化通知引用了不存在的 `app.scheduler.notify` 模块（Bug），失败重试无通知。服务器无公网，Telegram 是唯一获取运行状态的渠道。

改造为：每个任务先发短摘要文本，再发完整 Markdown 文件附件，彻底解决字符数限制问题。

### 代码修改清单

| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `app/notification/__init__.py` | TelegramChannel 新增 `send_document()` 文件上传，NotificationManager 新增 `send_report()` 方法 |
| 新建 | `app/scheduler/report.py` | 3 个 Markdown 报告生成函数（盘后链路/全市场优化/失败重试） |
| 修改 | `app/scheduler/jobs.py` | 盘后通知：删除 40 行纯文本构建逻辑，改用 report 模块 + send_report；失败重试：收集失败明细 + 末尾发送通知 |
| 修改 | `app/scheduler/market_opt_job.py` | 修复引用不存在的 `app.scheduler.notify` 模块，改用 NotificationManager + report 模块 |

### 覆盖的通知场景

| 任务 | 摘要文本 | Markdown 文件 |
|------|----------|---------------|
| 盘后链路 | 耗时/选股数/计划数/完成率 | 执行概况 + 策略分布 + 选股明细(全量) + 交易计划 + 涨跌分布 |
| 全市场优化 | 优化策略数/成功数/评分范围 | 每个策略 Top 10 参数组合表格 |
| 失败重试 | 重试/成功/仍失败数 | 失败明细列表（代码+错误原因） |

## 2026-02-28：盘后链路结果页面 + 全市场参数优化

### 设计思路

**盘后链路结果查看**：系统每日盘后自动执行选股并写入 `strategy_picks` 表，但之前前端无法查看历史选股结果。新增两个页面——「每日选股」按日期汇总展示，「盘后概览」整合任务执行、命中率和交易计划。

**全市场选股回放优化**：现有参数优化基于 Backtrader 单股回测（目标 Sharpe），无法评估选股策略的全市场实际表现。新增 `MarketOptimizer`，通过在历史交易日上回放选股管道来评估参数组合效果：
- 采样方式：间隔 4 天采样（120 天 → 约 30 个采样日），平衡精度和性能
- 评分公式：`score = hit_rate_5d × 0.5 + avg_return_5d × 0.3 - max_drawdown × 0.2`（偏命中率）
- 每周 cron 自动执行，最佳参数自动写入 `strategies.params` 表

### 代码修改清单

#### 后端修改
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `app/api/strategy.py` | +3 个 API 端点（daily-summary, by-date, post-market/overview） |
| 修改 | `app/api/optimization.py` | +3 个全市场优化端点（market-opt/run, result, list） |
| 修改 | `app/config.py` | +5 个配置项（market_opt_*） |
| 修改 | `app/scheduler/core.py` | 注册 weekly_market_optimization cron 任务 |
| 新建 | `app/optimization/market_optimizer.py` | MarketOptimizer 核心类 |
| 新建 | `app/scheduler/market_opt_job.py` | 每周全市场优化 cron 任务 |

#### 数据库变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `alembic/versions/h2b3c4d5e6f7_add_market_optimization_tasks.py` | market_optimization_tasks 表 |

#### 前端修改
| 操作 | 文件 | 说明 |
|------|------|------|
| 新建 | `web/src/types/postmarket.ts` | 盘后链路 + 全市场优化类型定义 |
| 新建 | `web/src/api/postmarket.ts` | API 函数 |
| 新建 | `web/src/pages/daily-picks/DailyPicksPage.tsx` | 每日选股结果页面 |
| 新建 | `web/src/pages/post-market/PostMarketPage.tsx` | 盘后概览页面 |
| 修改 | `web/src/App.tsx` | +2 个路由（/daily-picks, /post-market） |
| 修改 | `web/src/layouts/AppLayout.tsx` | +2 个菜单项 |
| 修改 | `web/src/pages/optimization/index.tsx` | 新增全市场优化 UI 区块 |

#### 配置变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `.env.example` | +5 个环境变量（MARKET_OPT_*） |

#### 文档变更
| 操作 | 文件 | 说明 |
|------|------|------|
| 修改 | `docs/design/02-详细设计-策略引擎.md` | 新增 §13 全市场选股回放参数优化 |
| 修改 | `docs/design/04-详细设计-前端与交互.md` | 新增 §1.3 每日选股结果页面 + §1.4 盘后概览页面 |
| 修改 | `docs/design/10-系统设计-定时任务调度.md` | 新增 weekly_market_optimization 任务 |
| 修改 | `docs/design/99-实施范围-V1与V2划分.md` | 更新参数优化模块为已实施 |
| 修改 | `CLAUDE.md` | 更新策略引擎架构说明 |
| 修改 | `README.md` | 更新功能特性（参数优化+前端界面） |

### 数据库变更

```sql
CREATE TABLE market_optimization_tasks (
    id SERIAL PRIMARY KEY,
    strategy_name VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'pending',  -- pending/running/completed/failed
    param_space JSONB,
    lookback_days INTEGER DEFAULT 120,
    total_combinations INTEGER,
    completed_combinations INTEGER DEFAULT 0,
    progress INTEGER DEFAULT 0,
    best_params JSONB,
    best_score NUMERIC(10,6),
    result_detail JSONB,
    auto_apply BOOLEAN DEFAULT true,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    finished_at TIMESTAMP
);
CREATE INDEX idx_mopt_strategy ON market_optimization_tasks (strategy_name);
CREATE INDEX idx_mopt_status ON market_optimization_tasks (status);
```

### 新增配置项

| 环境变量 | 默认值 | 说明 |
|---------|--------|------|
| MARKET_OPT_ENABLED | true | 是否启用每周全市场参数优化 |
| MARKET_OPT_CRON | 0 10 * * 6 | cron 表达式（默认周六 10:00） |
| MARKET_OPT_LOOKBACK_DAYS | 120 | 回看交易日数 |
| MARKET_OPT_AUTO_APPLY | true | 完成后是否自动应用最佳参数 |
| MARKET_OPT_MAX_CONCURRENCY | 4 | 最大并发参数组合数 |

### 新增 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/strategy/picks/daily-summary` | 每日选股汇总 |
| GET | `/api/v1/strategy/picks/by-date` | 指定日期选股明细 |
| GET | `/api/v1/strategy/post-market/overview` | 盘后概览 |
| POST | `/api/v1/optimization/market-opt/run` | 提交全市场优化任务 |
| GET | `/api/v1/optimization/market-opt/result/{task_id}` | 查询优化结果 |
| GET | `/api/v1/optimization/market-opt/list` | 优化任务列表 |

### 新增前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/daily-picks` | DailyPicksPage | 每日选股结果（汇总+展开明细） |
| `/post-market` | PostMarketPage | 盘后链路概览（统计卡片+任务日志+命中率+交易计划） |
