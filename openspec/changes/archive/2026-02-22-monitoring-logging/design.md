## Context

当前日志系统使用 Python logging 标准库，双输出（控制台 + 文件），纯文本格式 `%(asctime)s [%(levelname)s] %(name)s: %(message)s`。日志文件按环境隔离（app-dev.log / app-prod.log），无轮转策略。健康检查仅返回 `{"status": "ok"}`，不检测依赖。659 处日志调用分布在 52 个文件中，已有完善的 `time.monotonic()` 计时模式。

## Goals / Non-Goals

**Goals:**
- 生产环境 JSON 结构化日志，便于日志分析工具解析
- 日志轮转防止磁盘占满
- 深度健康检查，快速定位依赖故障
- API 请求性能监控，发现慢接口
- 任务执行历史持久化，支持回溯排查

**Non-Goals:**
- 不接入 ELK/Loki 等集中式日志系统（单机部署，文件日志足够）
- 不接入 Prometheus/Grafana（V2 后续考虑）
- 不修改现有 659 处日志调用的内容（仅改格式化器）
- 不做系统资源监控（CPU/内存/磁盘）

## Decisions

### D1: 结构化日志方案

**选择：** 标准库 logging + 自定义 JSONFormatter，不引入第三方依赖

**方案：**
- 自定义 `JSONFormatter`，输出 JSON 行格式（每行一个 JSON 对象）
- 开发环境（APP_ENV=development）使用可读的彩色文本格式
- 生产环境（APP_ENV=production）使用 JSON 格式
- JSON 字段：timestamp, level, logger, message, module, funcName, lineno, extra

**理由：** 单机部署场景，标准库足够。JSON 格式便于 `jq` 命令行分析，也兼容未来接入日志系统。

### D2: 日志轮转策略

**选择：** `RotatingFileHandler` 按大小轮转 + 错误日志独立文件

**配置：**
- 主日志：`logs/app.log`，单文件最大 50MB，保留 5 个备份
- 错误日志：`logs/app-error.log`，仅记录 WARNING 及以上，单文件最大 20MB，保留 10 个备份
- 控制台输出不受轮转影响

### D3: 健康检查设计

**选择：** 单一 `/health` 端点，支持 `?detail=true` 参数

**检查项：**
- 数据库：执行 `SELECT 1`，超时 3 秒
- Redis：执行 `PING`，超时 2 秒（Redis 不可用时标记 degraded 而非 unhealthy）
- Tushare：检查 token 是否配置（不实际调用 API，避免消耗配额）

**状态：**
- `healthy`：所有必需组件正常
- `degraded`：可选组件（Redis）不可用
- `unhealthy`：必需组件（数据库）不可用

**HTTP 状态码：** healthy/degraded 返回 200，unhealthy 返回 503

### D4: API 性能中间件

**选择：** FastAPI Middleware，记录每个请求的性能指标

**记录内容：** method, path, status_code, duration_ms, client_ip
**慢请求阈值：** 超过 1 秒的请求记录 WARNING 日志
**排除路径：** `/health`, `/docs`, `/openapi.json`（避免噪音）

### D5: 任务执行日志表

**选择：** 新增 `task_execution_log` 表，记录调度任务的执行历史

**字段：** id, task_name, status (running/success/failed), started_at, finished_at, duration_seconds, result_summary (JSONB), error_message, trade_date
**写入时机：** 盘后链路各步骤开始/结束时写入
**查询 API：** `GET /api/v1/tasks/logs` 支持按任务名、状态、日期范围过滤

## Risks / Trade-offs

- **JSON 日志可读性** → 开发环境保留文本格式，生产环境用 `jq` 工具辅助阅读
- **中间件性能开销** → `time.monotonic()` 开销极小（纳秒级），可忽略
- **任务日志表增长** → 每日约 20-30 条记录，年增长 ~10000 条，无需分区
- **健康检查频率** → 不做缓存，每次请求实时检测（单机场景无负载均衡器频繁探测）

## Open Questions

无
