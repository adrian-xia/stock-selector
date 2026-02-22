## ADDED Requirements

### Requirement: 结构化日志配置项
系统 SHALL 支持以下结构化日志配置项：

- `LOG_FORMAT`: 日志格式，`text` 或 `json`（默认根据 APP_ENV 自动选择：development=text, production=json）
- `LOG_FILE_MAX_BYTES`: 单个日志文件最大字节数（默认 52428800，即 50MB）
- `LOG_FILE_BACKUP_COUNT`: 日志文件保留备份数（默认 5）

#### Scenario: 配置项加载
- **WHEN** 应用启动加载配置
- **THEN** 结构化日志配置项 SHALL 从 .env 文件或环境变量加载
- **AND** 未配置时 SHALL 使用默认值

### Requirement: API 性能监控配置项
系统 SHALL 支持以下 API 性能监控配置项：

- `API_SLOW_REQUEST_THRESHOLD_MS`: 慢请求阈值毫秒数（默认 1000）

#### Scenario: 慢请求阈值配置
- **WHEN** .env 文件包含 `API_SLOW_REQUEST_THRESHOLD_MS=2000`
- **THEN** `settings.api_slow_request_threshold_ms` SHALL 为 2000

### Requirement: 健康检查配置项
系统 SHALL 支持以下健康检查配置项：

- `HEALTH_CHECK_TIMEOUT`: 健康检查超时秒数（默认 3）

#### Scenario: 健康检查超时配置
- **WHEN** .env 文件包含 `HEALTH_CHECK_TIMEOUT=5`
- **THEN** `settings.health_check_timeout` SHALL 为 5
