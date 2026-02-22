## ADDED Requirements

### Requirement: JSON 结构化日志格式化器
系统 SHALL 提供 `JSONFormatter` 类，将日志记录格式化为 JSON 行格式（每行一个 JSON 对象）。

JSON 字段：
- `timestamp`: ISO 8601 格式时间戳
- `level`: 日志级别（INFO/WARNING/ERROR 等）
- `logger`: logger 名称
- `message`: 日志消息
- `module`: 模块名
- `funcName`: 函数名
- `lineno`: 行号
- `extra`: 额外字段（如有）

#### Scenario: JSON 格式输出
- **WHEN** 使用 JSONFormatter 格式化一条 INFO 日志
- **THEN** 输出 SHALL 为单行合法 JSON，包含 timestamp、level、logger、message 等字段

#### Scenario: 异常信息包含在 JSON 中
- **WHEN** 日志记录包含异常信息（exc_info）
- **THEN** JSON 输出 SHALL 包含 `traceback` 字段，值为异常堆栈字符串

### Requirement: 环境感知日志格式切换
`setup_logging()` SHALL 根据 `APP_ENV` 配置选择日志格式：
- `development`：使用可读的文本格式（当前格式）
- `production`：使用 JSON 结构化格式

#### Scenario: 开发环境使用文本格式
- **WHEN** `APP_ENV=development` 且调用 `setup_logging()`
- **THEN** 控制台和文件日志 SHALL 使用文本格式 `%(asctime)s [%(levelname)s] %(name)s: %(message)s`

#### Scenario: 生产环境使用 JSON 格式
- **WHEN** `APP_ENV=production` 且调用 `setup_logging()`
- **THEN** 控制台和文件日志 SHALL 使用 JSONFormatter 输出 JSON 行格式

### Requirement: 日志文件轮转
系统 SHALL 使用 `RotatingFileHandler` 实现日志文件轮转。

配置：
- 主日志文件：`logs/app.log`，单文件最大 `LOG_FILE_MAX_BYTES`（默认 50MB），保留 `LOG_FILE_BACKUP_COUNT`（默认 5）个备份
- 错误日志文件：`logs/app-error.log`，仅记录 WARNING 及以上级别，单文件最大 20MB，保留 10 个备份

#### Scenario: 主日志轮转
- **WHEN** `logs/app.log` 文件大小超过 50MB
- **THEN** SHALL 自动轮转为 `app.log.1`，新日志写入新的 `app.log`
- **AND** 最多保留 5 个备份文件

#### Scenario: 错误日志独立记录
- **WHEN** 产生一条 WARNING 或 ERROR 级别日志
- **THEN** 该日志 SHALL 同时写入 `logs/app.log` 和 `logs/app-error.log`

#### Scenario: INFO 日志不写入错误文件
- **WHEN** 产生一条 INFO 级别日志
- **THEN** 该日志 SHALL 写入 `logs/app.log` 但不写入 `logs/app-error.log`

### Requirement: 第三方库日志抑制
`setup_logging()` SHALL 将以下第三方库的日志级别设置为 WARNING，避免噪音：httpcore, httpx, asyncio, sqlalchemy.engine, apscheduler。

#### Scenario: 第三方库 DEBUG 日志被抑制
- **WHEN** httpx 库产生 DEBUG 级别日志
- **THEN** 该日志 SHALL 不被输出（被 WARNING 级别过滤）
