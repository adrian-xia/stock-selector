## Context

数据采集模块提供 `DataManager.sync_daily()`、`sync_stock_list()`、`sync_trade_calendar()` 等同步方法；技术指标模块提供 `compute_incremental()` 增量计算；策略管道提供 `execute_pipeline()` 执行选股。CLI 模块（`app/data/cli.py`）已有 `sync-daily`、`update-indicators` 等命令。

当前所有操作需手动触发。V1 单人使用，不存在多实例并发，无需分布式锁和 DAG 引擎。

现有依赖：
- `DataManager.sync_daily()` — 增量同步单只股票日线
- `DataManager.is_trade_day(date)` — 交易日校验
- `DataManager.sync_stock_list()` — 全量同步股票列表
- `compute_incremental(session_factory, target_date)` — 增量计算技术指标
- `execute_pipeline(session_factory, strategy_names, target_date)` — 执行选股管道
- `StrategyFactory.get_all()` — 获取所有已注册策略

约束：
- APScheduler 尚未安装，需添加到 pyproject.toml
- V1 不用 Redis 分布式锁、不建执行日志表、不做 HTTP 管理 API
- 任务链为线性串行，失败写日志即可

## Goals / Non-Goals

**Goals:**
- 每个交易日盘后自动执行完整链路：日线同步 → 技术指标计算 → 策略管道执行
- 非交易日自动跳过盘后任务
- 每周末自动同步股票列表
- 提供 CLI 命令手动触发完整链路或单个任务
- 调度器随 FastAPI 应用启动/停止，无需额外进程

**Non-Goals:**
- 不实现 Redis 分布式锁（V1 单实例）
- 不实现 DAG 引擎和并行任务执行（V1 线性串行）
- 不建 scheduler_tasks / scheduler_task_logs 数据库表（V1 用日志）
- 不实现 HTTP 管理 API（V1 用 CLI）
- 不实现 Telegram/邮件告警（V1 日志输出）
- 不实现 AI 分析任务调度（AI 模块尚未实现）

## Decisions

### Decision 1: APScheduler Job Store — SQLite vs 内存

**选择：内存 Job Store（MemoryJobStore）**

- 设计文档建议 PostgreSQL Job Store，V1 简化方案建议 SQLite
- V1 任务定义是硬编码的（代码中注册），不需要持久化 Job 定义
- 服务重启后 APScheduler 重新注册所有任务即可，无状态丢失
- 内存 Job Store 零依赖，无需额外文件或数据库连接
- 如果 V2 需要动态任务管理，再切换到 SQLAlchemy Job Store

### Decision 2: 任务链执行 — 串行函数调用 vs APScheduler 依赖

**选择：串行函数调用（单个 chain 函数）**

- APScheduler 本身不支持任务依赖（需要自建 DAG 引擎）
- V1 盘后链路是简单的线性串行：sync → indicators → pipeline
- 用一个 `run_post_market_chain()` 函数按顺序调用各步骤
- 任一步骤失败则中断链路，记录日志，后续步骤不执行
- 比 DAG 引擎简单得多，且完全满足 V1 需求

### Decision 3: 日线同步策略 — 全量 vs 增量

**选择：增量同步（仅同步当日数据）**

- 全量同步 5000+ 只股票耗时过长（>30 分钟）
- 盘后只需同步当日新增的日线数据
- 查询所有上市状态的股票，逐只调用 `DataManager.sync_daily(code, today, today)`
- 失败的股票记录日志，不阻塞其他股票的同步

### Decision 4: 调度器生命周期 — 独立进程 vs 嵌入 FastAPI

**选择：嵌入 FastAPI lifespan**

- V1 单人使用，不需要独立的调度进程
- 在 `app/main.py` 的 lifespan 中启动 `AsyncIOScheduler`
- 应用启动时注册所有 cron 任务，关闭时优雅停止调度器
- CLI 命令独立运行（不依赖 FastAPI），直接调用任务函数

### Decision 5: 策略管道触发 — 全部策略 vs 可配置

**选择：默认执行全部已注册策略**

- `StrategyFactory.get_all()` 返回所有 12 种策略
- 盘后自动执行时使用全部策略，`top_n=50`
- CLI 手动触发时可通过参数指定策略子集

### Decision 6: 目录结构

```
app/scheduler/
├── __init__.py
├── core.py          # create_scheduler()、启动/停止、任务注册
├── jobs.py          # 盘后链路、周末任务、各步骤实现
└── cli.py           # CLI 命令：run-chain、run-job
```

### Decision 7: Cron 时间配置

| 任务 | Cron 表达式 | 说明 |
|:---|:---|:---|
| 盘后链路 | `15:30 周一至周五` | 收盘后 30 分钟，等数据源更新 |
| 股票列表同步 | `08:00 周六` | 周末全量同步 |

- 盘后链路设在 15:30 而非 15:05，因为 BaoStock 数据通常在 15:15-15:30 才完全可用
- 时间可通过配置项调整

## Risks / Trade-offs

- **[可靠性] 嵌入 FastAPI 的调度器** → 如果 FastAPI 进程崩溃，调度器也会停止。V1 可接受，生产环境可用 systemd 自动重启。V2 可考虑独立调度进程
- **[性能] 串行执行全量股票同步** → 5000+ 只股票逐只同步可能耗时 10-20 分钟。V1 可接受（盘后时间充裕）。可通过批量并发优化
- **[数据完整性] 增量同步失败的股票** → 部分股票同步失败不会阻塞链路，但会导致这些股票的技术指标和策略结果缺失。通过日志记录失败股票，下次同步时自动补齐
- **[简化] 无执行日志表** → 任务执行历史只在日志文件中，无法通过 API 查询。V2 可加 scheduler_task_logs 表
