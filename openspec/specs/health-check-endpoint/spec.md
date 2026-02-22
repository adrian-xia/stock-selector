## ADDED Requirements

### Requirement: 深度健康检查端点
系统 SHALL 提供 `GET /health` 端点，检测所有关键依赖的可用性并返回各组件状态。

检查项：
- `database`：执行 `SELECT 1`，超时 `HEALTH_CHECK_TIMEOUT`（默认 3 秒）
- `redis`：执行 `PING`，超时 2 秒（Redis 为可选组件）
- `tushare`：检查 `TUSHARE_TOKEN` 是否已配置（不实际调用 API）

状态定义：
- `healthy`：所有必需组件（database）正常
- `degraded`：可选组件（redis）不可用，必需组件正常
- `unhealthy`：必需组件（database）不可用

#### Scenario: 所有组件正常
- **WHEN** 调用 `GET /health` 且数据库和 Redis 均可用
- **THEN** SHALL 返回 HTTP 200，body 包含 `{"status": "healthy", "components": {"database": {"status": "up", "latency_ms": ...}, "redis": {"status": "up", "latency_ms": ...}, "tushare": {"status": "configured"}}}`

#### Scenario: Redis 不可用
- **WHEN** 调用 `GET /health` 且 Redis 连接失败
- **THEN** SHALL 返回 HTTP 200，body 包含 `{"status": "degraded", "components": {"database": {"status": "up"}, "redis": {"status": "down", "error": "..."}, "tushare": {"status": "configured"}}}`

#### Scenario: 数据库不可用
- **WHEN** 调用 `GET /health` 且数据库连接失败
- **THEN** SHALL 返回 HTTP 503，body 包含 `{"status": "unhealthy", "components": {"database": {"status": "down", "error": "..."}}}`

#### Scenario: 简单健康检查
- **WHEN** 调用 `GET /health` 且不带参数
- **THEN** SHALL 执行深度检查并返回完整组件状态

### Requirement: 健康检查响应模型
健康检查响应 SHALL 使用 Pydantic 模型定义，包含 status 和 components 字段。

#### Scenario: 响应符合模型定义
- **WHEN** 健康检查端点返回响应
- **THEN** 响应 SHALL 符合 `HealthCheckResponse` 模型，包含 `status`（枚举）和 `components`（字典）字段
