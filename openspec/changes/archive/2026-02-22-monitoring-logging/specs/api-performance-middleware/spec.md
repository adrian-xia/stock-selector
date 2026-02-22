## ADDED Requirements

### Requirement: 请求性能日志中间件
系统 SHALL 提供 FastAPI 中间件 `RequestPerformanceMiddleware`，记录每个 HTTP 请求的性能指标。

记录字段：method, path, status_code, duration_ms, client_ip

#### Scenario: 正常请求记录性能日志
- **WHEN** 客户端发起 `GET /api/v1/strategy/run` 请求且响应耗时 200ms
- **THEN** SHALL 记录 INFO 日志：method=GET, path=/api/v1/strategy/run, status_code=200, duration_ms=200

#### Scenario: 慢请求告警
- **WHEN** 请求响应时间超过 `API_SLOW_REQUEST_THRESHOLD_MS`（默认 1000ms）
- **THEN** SHALL 记录 WARNING 日志，标记为慢请求

#### Scenario: 排除噪音路径
- **WHEN** 请求路径为 `/health`、`/docs`、`/openapi.json`
- **THEN** SHALL 不记录性能日志

### Requirement: 中间件注册
`RequestPerformanceMiddleware` SHALL 在 FastAPI 应用启动时自动注册。

#### Scenario: 应用启动时注册中间件
- **WHEN** FastAPI 应用启动
- **THEN** `RequestPerformanceMiddleware` SHALL 被添加到中间件栈
