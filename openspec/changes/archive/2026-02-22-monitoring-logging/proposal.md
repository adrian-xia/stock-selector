## Why

当前系统有 659 处日志调用，但全部使用纯文本格式，缺乏结构化日志、健康检查端点和 API 性能监控。生产环境排查问题时需要手动 grep 日志文件，无法快速定位错误和性能瓶颈。健康检查仅有基础的 `/health` 返回 `{"status": "ok"}`，不检测数据库、Redis、Tushare 等关键依赖的实际可用性。

## What Changes

- 结构化日志：生产环境输出 JSON 格式日志，开发环境保留可读格式；日志轮转（按大小/时间）；错误日志独立文件
- API 性能中间件：FastAPI 中间件记录每个请求的响应时间、状态码、路径；慢查询告警
- 健康检查端点：`/health` 增强为深度检查（数据库连接、Redis 连接、Tushare API 可用性），返回各组件状态
- 任务执行日志表：盘后链路、数据同步等任务的执行记录持久化到数据库，支持查询历史执行状态和耗时
- 任务执行日志 API：查询任务执行历史

## Capabilities

### New Capabilities
- `structured-logging`: 结构化日志配置（JSON 格式、日志轮转、错误日志分离、环境感知格式切换）
- `api-performance-middleware`: FastAPI 请求性能中间件（响应时间、状态码、慢请求告警）
- `health-check-endpoint`: 深度健康检查端点（数据库、Redis、Tushare 依赖检测）
- `task-execution-log`: 任务执行日志持久化（数据库表 + 写入逻辑 + 查询 API）

### Modified Capabilities
- `app-config`: 新增结构化日志和健康检查相关配置项

## Impact

- **代码：** 主要修改 `app/logger.py`（日志配置重构）、`app/main.py`（中间件注册）、`app/api/`（新增端点）
- **数据库：** 新增 `task_execution_log` 表（Alembic 迁移）
- **依赖：** 无新 Python 依赖（python-json-logger 可选，标准库 logging 足够）
- **配置：** 新增日志格式、轮转、健康检查超时等配置项
- **兼容性：** 开发环境默认保留可读格式，生产环境切换到 JSON
