## Why

当前系统缺少生产环境部署和运维支持，无法方便地打包、部署和管理服务。同时，定时任务只同步当天数据，服务停机期间的数据会永久缺失，缺少数据完整性检查和自动补齐机制（断点续传）。这些问题阻碍了系统在生产环境的稳定运行和持续维护。

## What Changes

- 新增打包命令，支持将应用打包为可部署的 tarball 格式（包含源代码、依赖锁文件、配置模板、README）
- 新增跨平台服务管理命令集，支持 Linux（systemd）和 Mac（launchd）：
  - 服务注册：将应用注册为系统服务，支持开机自启动
  - 服务启动/停止：支持前台和后台启动模式
  - 服务注销：移除系统服务注册
  - 优雅关闭：等待任务完成后再停止服务
- 新增数据完整性检查和自动补齐机制（断点续传）：
  - 启动时检查：检测最近 N 天数据是否完整，自动补齐缺失的交易日数据
  - 手动补齐命令：支持指定日期范围补齐数据，避免重复同步已有数据
  - 初始化向导：首次部署时引导用户初始化历史数据（如最近 1 年或 3 年）
- 增强调度器启动逻辑，集成数据完整性检查，支持 `--skip-integrity-check` 参数跳过检查

## Capabilities

### New Capabilities

- `deployment-packaging`: 应用打包能力，支持创建可部署的 tarball 包（包含源代码、uv.lock、.env.example、README）
- `service-management`: 跨平台服务管理能力，支持服务注册、启动、停止、注销（Linux systemd / Mac launchd）
- `data-integrity-check`: 数据完整性检查和自动补齐能力，支持启动时检查、手动补齐命令、初始化向导
- `data-initialization`: 数据初始化向导能力，引导用户首次部署时初始化历史数据（1 年 / 3 年 / 自定义范围）

### Modified Capabilities

- `scheduler-jobs`: 增强启动逻辑，集成数据完整性检查，支持启动参数控制检查行为

## Impact

**新增文件：**
- `scripts/package.py` - 打包脚本
- `scripts/service.py` - 服务管理脚本（支持 Linux/Mac）
- `scripts/init_data.py` - 数据初始化向导脚本
- `templates/stock-selector.service` - systemd 服务文件模板
- `templates/com.stock-selector.plist` - launchd plist 文件模板

**修改文件：**
- `app/scheduler/core.py` - 添加启动时数据完整性检查
- `app/data/manager.py` - 新增 `detect_missing_dates()` 方法
- `app/data/cli.py` - 新增 `backfill-daily` 命令
- `app/config.py` - 新增 `DATA_INTEGRITY_CHECK_DAYS` 配置项
- `.env.example` - 新增数据完整性检查配置说明
- `README.md` - 补充部署、服务管理、数据初始化说明
- `CLAUDE.md` - 补充部署和运维相关说明

**依赖变更：**
- 无新增 Python 依赖（使用标准库和现有依赖）

**运维影响：**
- 提供标准化的部署流程，简化生产环境部署
- 支持系统服务管理，简化运维操作
- 启动时自动检查数据完整性，避免数据缺失
- 支持断点续传，服务停机后重启不会丢失数据

**数据安全：**
- 数据补齐功能会检查已有数据，避免重复同步
- 初始化向导提供数据范围选择，避免不必要的全量同步
