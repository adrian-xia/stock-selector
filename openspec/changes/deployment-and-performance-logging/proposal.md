## Why

当前系统缺少生产环境部署和运维支持，无法方便地打包、部署和管理服务。同时，增量任务（日线同步、技术指标计算等）的性能瓶颈不明确，缺少详细的耗时日志用于性能分析和优化。此外，定时任务只同步当天数据，服务停机期间的数据会永久缺失，缺少数据完整性检查和自动补齐机制。这些问题阻碍了系统在生产环境的稳定运行和持续优化。

## What Changes

- 新增打包命令，支持将应用打包为可部署的格式（包含依赖、配置、启动脚本）
- 新增跨平台服务管理命令集，支持 Mac、Linux、Windows 三个操作系统：
  - 服务注册：将应用注册为系统服务，支持开机自启动
  - 服务启动/停止：支持前台和后台启动模式
  - 服务注销：移除系统服务注册
- 新增数据完整性检查和自动补齐机制：
  - 启动时检查：检测最近 N 天数据是否完整，自动补齐缺失的交易日数据
  - 手动补齐命令：支持指定日期范围补齐数据，避免重复同步已有数据
  - 初始化向导：首次部署时引导用户初始化历史数据（如最近 1 年）
- 增强增量任务的性能日志：
  - 日线同步：记录每批次、每只股票的耗时
  - 技术指标计算：记录每个指标的计算耗时
  - 缓存刷新：记录缓存预热和刷新的耗时
- 在 PROJECT_TASKS.md 中新增"性能优化"章节，跟踪性能瓶颈和优化任务
- 更新设计文档，补充部署和运维相关的架构说明

## Capabilities

### New Capabilities

- `deployment-packaging`: 应用打包能力，支持创建可部署的应用包（包含依赖、配置、启动脚本）
- `service-management`: 跨平台服务管理能力，支持服务注册、启动、停止、注销（Mac/Linux/Windows）
- `data-integrity-check`: 数据完整性检查和自动补齐能力，支持启动时检查、手动补齐、初始化向导
- `performance-logging`: 性能日志增强能力，为增量任务添加详细的耗时日志和性能指标

### Modified Capabilities

- `scheduler-jobs`: 增强定时任务的性能日志，添加详细的耗时统计和性能指标输出

## Impact

**新增文件：**
- `scripts/package.py` - 打包脚本
- `scripts/service.py` - 服务管理脚本（支持 Mac/Linux/Windows）
- `scripts/install_service.sh` - Linux/Mac 服务安装脚本
- `scripts/install_service.ps1` - Windows 服务安装脚本
- `scripts/check_data_integrity.py` - 数据完整性检查和补齐脚本
- `scripts/init_data.py` - 数据初始化向导脚本

**修改文件：**
- `app/scheduler/jobs.py` - 增强性能日志（sync_daily_step, compute_tech_step, cache_refresh_step）
- `app/scheduler/core.py` - 添加启动时数据完整性检查
- `app/data/batch.py` - 添加详细的批次和单股耗时日志
- `app/data/indicator.py` - 添加指标计算耗时日志
- `app/cache/tech_cache.py` - 添加缓存操作耗时日志
- `app/data/cli.py` - 新增数据补齐命令（backfill-daily）
- `PROJECT_TASKS.md` - 新增"性能优化"章节
- `README.md` - 补充部署和服务管理说明
- 设计文档（`~/Developer/Design/stock-selector-design/`）- 补充部署架构和运维说明

**依赖变更：**
- 可能需要添加打包相关的依赖（如 PyInstaller 或 zipapp）
- 服务管理可能需要平台特定的依赖（如 Windows 的 pywin32）

**运维影响：**
- 提供标准化的部署流程
- 支持系统服务管理，简化运维操作
- 启动时自动检查数据完整性，避免数据缺失
- 性能日志增强后，日志量会增加，需要注意日志轮转和存储

**数据安全：**
- 数据补齐功能会检查已有数据，避免重复同步
- 支持断点续传，服务停机后重启不会丢失数据
- 初始化向导提供数据范围选择，避免不必要的全量同步
