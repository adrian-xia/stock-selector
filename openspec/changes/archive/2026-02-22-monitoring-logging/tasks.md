## 1. 结构化日志

- [x] 1.1 实现 `JSONFormatter` 类（app/logger.py），输出 JSON 行格式日志
- [x] 1.2 重构 `setup_logging()` 支持环境感知格式切换（development=text, production=json）
- [x] 1.3 实现日志文件轮转（RotatingFileHandler，主日志 50MB×5 + 错误日志 20MB×10）
- [x] 1.4 新增配置项 LOG_FORMAT、LOG_FILE_MAX_BYTES、LOG_FILE_BACKUP_COUNT（app/config.py）
- [x] 1.5 为 JSONFormatter 和 setup_logging 编写单元测试

## 2. API 性能中间件

- [x] 2.1 实现 `RequestPerformanceMiddleware`（app/api/middleware.py），记录请求性能指标
- [x] 2.2 实现慢请求告警（超过阈值记录 WARNING）和噪音路径排除
- [x] 2.3 新增配置项 API_SLOW_REQUEST_THRESHOLD_MS（app/config.py）
- [x] 2.4 在 FastAPI 应用中注册中间件（app/main.py）
- [x] 2.5 为中间件编写单元测试

## 3. 健康检查端点

- [x] 3.1 实现健康检查响应模型（app/api/health.py），Pydantic 模型定义
- [x] 3.2 实现深度健康检查逻辑（数据库 SELECT 1、Redis PING、Tushare token 检测）
- [x] 3.3 新增配置项 HEALTH_CHECK_TIMEOUT（app/config.py）
- [x] 3.4 替换现有 `/health` 端点为深度检查版本（app/main.py）
- [x] 3.5 为健康检查端点编写单元测试

## 4. 任务执行日志

- [x] 4.1 创建 Alembic 迁移脚本：task_execution_log 表（含索引）
- [x] 4.2 实现 `TaskLogger` 类（app/scheduler/task_logger.py），提供 start/finish/track 方法
- [x] 4.3 在盘后链路中集成 TaskLogger（app/scheduler/jobs.py），记录各步骤执行状态
- [x] 4.4 实现任务执行日志查询 API（app/api/task_log.py），支持按名称/状态/日期过滤
- [x] 4.5 在 FastAPI 中注册任务日志路由（app/main.py）
- [x] 4.6 为 TaskLogger 和查询 API 编写单元测试

## 5. 文档与配置更新

- [x] 5.1 更新 .env.example 新增所有配置项
- [x] 5.2 更新 docs/design/99-实施范围-V1与V2划分.md 标记监控与日志增强为已实施
- [x] 5.3 更新 README.md 说明新功能
- [x] 5.4 更新 CLAUDE.md 同步技术栈和目录结构
- [x] 5.5 更新 PROJECT_TASKS.md 标记 Change 14 已完成
