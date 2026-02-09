## 1. 创建数据嗅探模块

- [x] 1.1 创建 `app/data/probe.py` 文件
- [x] 1.2 实现 `probe_daily_data()` 函数，查询样本股票的指定日期数据
- [x] 1.3 实现阈值判断逻辑（≥80% 样本有数据则返回 True）
- [x] 1.4 添加性能日志记录（嗅探耗时）
- [x] 1.5 添加详细的中文注释和类型注解

## 2. 创建任务状态管理模块

- [x] 2.1 创建 `app/scheduler/state.py` 文件
- [x] 2.2 定义 `SyncState` 枚举（pending/probing/syncing/completed/failed）
- [x] 2.3 实现 `SyncStateManager` 类
- [x] 2.4 实现 `get_state()` 方法，从 Redis 读取状态
- [x] 2.5 实现 `set_state()` 方法，写入状态到 Redis（TTL 7 天）
- [x] 2.6 实现 `is_completed()` 方法，检查任务是否已完成
- [x] 2.7 实现 `increment_probe_count()` 方法，递增嗅探计数
- [x] 2.8 实现 `save_probe_job_id()` 和 `get_probe_job_id()` 方法
- [x] 2.9 添加详细的中文注释和类型注解

## 3. 创建通知报警模块

- [x] 3.1 创建 `app/notification/__init__.py` 文件
- [x] 3.2 定义 `NotificationLevel` 枚举（INFO/WARNING/ERROR）
- [x] 3.3 实现 `NotificationManager` 类
- [x] 3.4 实现 `send()` 方法（V1 仅记录日志）
- [x] 3.5 添加元数据支持（记录到日志中）
- [x] 3.6 添加详细的中文注释和类型注解
- [x] 3.7 在注释中说明 V2 扩展点（接入企业微信/钉钉等）

## 4. 创建自动更新任务模块

- [x] 4.1 创建 `app/scheduler/auto_update.py` 文件
- [x] 4.2 实现 `auto_update_job()` 函数（每日 15:30 触发）
- [x] 4.3 在 `auto_update_job()` 中实现交易日校验逻辑
- [x] 4.4 在 `auto_update_job()` 中实现任务状态检查（避免重复执行）
- [x] 4.5 在 `auto_update_job()` 中实现数据嗅探逻辑
- [x] 4.6 在 `auto_update_job()` 中实现立即同步逻辑（数据已就绪）
- [x] 4.7 在 `auto_update_job()` 中实现启动嗅探任务逻辑（数据未就绪）
- [x] 4.8 实现 `probe_and_sync_job()` 函数（每 15 分钟触发）
- [x] 4.9 在 `probe_and_sync_job()` 中实现任务状态检查
- [x] 4.10 在 `probe_and_sync_job()` 中实现超时检查（18:00）
- [x] 4.11 在 `probe_and_sync_job()` 中实现数据嗅探和同步逻辑
- [x] 4.12 在 `probe_and_sync_job()` 中实现停止嗅探任务逻辑
- [x] 4.13 在 `probe_and_sync_job()` 中实现超时报警逻辑
- [x] 4.14 添加详细的中文注释和类型注解
- [x] 4.15 添加完整的日志记录（任务启动、嗅探结果、状态变更等）

## 5. 修改配置模块

- [x] 5.1 在 `app/config.py` 中新增 `auto_update_enabled` 配置项（默认 True）
- [x] 5.2 在 `app/config.py` 中新增 `auto_update_probe_interval` 配置项（默认 15 分钟）
- [x] 5.3 在 `app/config.py` 中新增 `auto_update_probe_timeout` 配置项（默认 18:00）
- [x] 5.4 在 `app/config.py` 中新增 `auto_update_probe_stocks` 配置项（默认 5 只大盘股）
- [x] 5.5 在 `app/config.py` 中新增 `auto_update_probe_threshold` 配置项（默认 0.8）
- [x] 5.6 在 `app/config.py` 中新增 `scheduler_auto_update_cron` 配置项（默认 "30 15 * * 1-5"）
- [x] 5.7 添加配置项的中文注释

## 6. 修改环境变量示例

- [x] 6.1 在 `.env.example` 中新增 `AUTO_UPDATE_ENABLED` 环境变量
- [x] 6.2 在 `.env.example` 中新增 `AUTO_UPDATE_PROBE_INTERVAL` 环境变量
- [x] 6.3 在 `.env.example` 中新增 `AUTO_UPDATE_PROBE_TIMEOUT` 环境变量
- [x] 6.4 在 `.env.example` 中新增 `AUTO_UPDATE_PROBE_STOCKS` 环境变量
- [x] 6.5 在 `.env.example` 中新增 `AUTO_UPDATE_PROBE_THRESHOLD` 环境变量
- [x] 6.6 在 `.env.example` 中新增 `SCHEDULER_AUTO_UPDATE_CRON` 环境变量
- [x] 6.7 添加配置项的中文注释说明

## 7. 修改调度器核心模块

- [x] 7.1 在 `app/scheduler/core.py` 的 `register_jobs()` 函数中移除原有盘后链路任务注册
- [x] 7.2 在 `app/scheduler/core.py` 的 `register_jobs()` 函数中新增自动更新任务注册
- [x] 7.3 添加配置项检查（`auto_update_enabled`），支持禁用自动更新
- [x] 7.4 使用 `scheduler_auto_update_cron` 配置项设置触发时间
- [x] 7.5 保留周末股票列表同步任务注册
- [x] 7.6 添加日志记录（注册任务、禁用任务等）

## 8. 单元测试

- [x] 8.1 创建 `tests/unit/test_probe.py` 文件
- [x] 8.2 测试数据嗅探成功场景（样本股票有数据）
- [x] 8.3 测试数据嗅探失败场景（样本股票无数据）
- [x] 8.4 测试阈值计算逻辑
- [x] 8.5 创建 `tests/unit/test_state.py` 文件
- [x] 8.6 测试状态流转（pending → probing → syncing → completed）
- [x] 8.7 测试嗅探计数递增
- [x] 8.8 测试任务 ID 存储和获取
- [x] 8.9 创建 `tests/unit/test_notification.py` 文件
- [x] 8.10 测试日志记录（V1 实现）

## 9. 集成测试

- [x] 9.1 创建 `tests/integration/test_auto_update.py` 文件
- [x] 9.2 测试场景 1：交易日 15:30 触发，数据已就绪
- [x] 9.3 测试场景 2：交易日 15:30 触发，数据未就绪，嗅探成功
- [x] 9.4 测试场景 3：交易日 15:30 触发，数据未就绪，超时报警
- [x] 9.5 测试场景 4：非交易日 15:30 触发

## 10. 手动验证

- [x] 10.1 检查配置是否正确加载（`uv run python -c "from app.config import settings; print(settings.auto_update_enabled)"`）
- [x] 10.2 手动触发嗅探测试（验证 `probe_daily_data()` 函数）
- [x] 10.3 检查 Redis 状态存储（`redis-cli KEYS sync_status:*`）
- [x] 10.4 启动服务，观察日志中是否有 "注册任务：自动数据更新" 记录
- [x] 10.5 等待 15:30 自动触发，观察日志输出
- [x] 10.6 检查数据是否同步成功
- [x] 10.7 检查 Redis 状态是否正确更新

## 11. 文档更新

- [x] 11.1 更新 `README.md` 中的功能特性，说明自动数据更新机制
- [x] 11.2 更新 `README.md` 中的配置说明，添加自动更新配置项
- [x] 11.3 更新 `README.md` 中的测试数量统计
- [x] 11.4 更新 `CLAUDE.md` 中的技术栈，说明通知报警模块
- [x] 11.5 更新 `CLAUDE.md` 中的 V1 范围，说明自动更新系统
- [x] 11.6 更新 `CLAUDE.md` 中的目录结构，添加新增模块
