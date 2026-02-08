## Context

当前系统已实现核心功能（数据采集、策略引擎、回测、前端），但缺少生产环境部署和运维支持。主要问题：

1. **部署困难**：无标准化打包流程，手动部署容易遗漏文件或配置
2. **服务管理缺失**：无法注册为系统服务，需要手动启动和管理进程
3. **数据断点续传缺失**：定时任务只同步当天数据，服务停机期间的数据会永久缺失
4. **首次部署复杂**：新环境部署需要手动初始化历史数据，缺少向导引导

**技术栈约束：**
- Python 3.12 + FastAPI + SQLAlchemy
- 包管理：uv（后端）
- 数据库：PostgreSQL
- 目标平台：Linux（systemd）、macOS（launchd）
- V1 范围：不支持 Windows、不使用 Docker

**利益相关方：**
- 开发者：需要简化部署流程
- 运维人员：需要标准化的服务管理
- 最终用户：需要数据完整性保障

## Goals / Non-Goals

**Goals:**
- 提供标准化的打包流程，生成可部署的 tarball
- 支持 Linux 和 macOS 的系统服务管理（安装、启动、停止、卸载）
- 实现数据完整性检查和自动补齐（断点续传）
- 提供交互式数据初始化向导，简化首次部署
- 支持优雅关闭，避免任务中断

**Non-Goals:**
- 不支持 Windows 平台（V2 再考虑）
- 不使用 Docker 容器化（V1 直接运行）
- 不实现分布式部署（单机部署）
- 不实现热更新或零停机部署
- 不实现自动化 CI/CD 流程

## Decisions

### 1. 打包格式：使用 tarball 而非 PyInstaller

**决策：** 使用 Python 标准库 `tarfile` 创建 `.tar.gz` 包，包含源代码和依赖锁文件。

**理由：**
- **简单可靠**：tarball 是 Unix/Linux 标准格式，无需额外依赖
- **透明可审计**：用户可以解压查看所有文件，便于审计和调试
- **依赖管理清晰**：使用 `uv.lock` 锁定依赖版本，部署时用 `uv sync` 安装
- **避免 PyInstaller 问题**：PyInstaller 打包后体积大、启动慢、调试困难

**替代方案：**
- PyInstaller：打包为单个可执行文件，但体积大（100+ MB）、不透明、调试困难
- Wheel：Python 标准打包格式，但不适合包含配置文件和文档的应用

**包内容：**
```
stock-selector-<version>.tar.gz
├── app/                    # 源代码
├── scripts/                # 工具脚本
├── templates/              # 服务文件模板
├── uv.lock                 # 依赖锁文件
├── .env.example            # 配置模板
└── README.md               # 文档
```

### 2. 服务管理：平台原生服务管理器

**决策：** 使用平台原生的服务管理器（Linux systemd / macOS launchd），而非第三方工具。

**理由：**
- **系统集成**：原生服务管理器与操作系统深度集成，支持开机自启、日志管理、资源限制
- **无额外依赖**：不需要安装 supervisord、pm2 等第三方工具
- **标准化**：systemd 和 launchd 是各自平台的标准，运维人员熟悉
- **可靠性**：原生服务管理器经过充分测试，稳定性高

**替代方案：**
- supervisord：需要额外安装，配置复杂，不支持 macOS
- pm2：Node.js 工具，不适合 Python 应用
- nohup + screen：手动管理，不支持开机自启，不可靠

**实现方式：**
- Linux：创建 `/etc/systemd/system/stock-selector.service` 文件
- macOS：创建 `~/Library/LaunchAgents/com.stock-selector.plist` 文件
- 统一接口：`scripts/service.py` 提供统一的命令行接口（install/start/stop/uninstall）

### 3. 数据完整性检查：启动时主动检查 + 手动补齐

**决策：** 在调度器启动时主动检查最近 N 天数据完整性，自动补齐缺失数据。同时提供手动补齐命令。

**理由：**
- **自动化**：启动时自动检查，无需人工干预
- **可配置**：通过 `DATA_INTEGRITY_CHECK_DAYS` 配置检查窗口（默认 30 天）
- **可跳过**：支持 `--skip-integrity-check` 参数，紧急情况下快速启动
- **手动补齐**：提供 CLI 命令，支持指定日期范围补齐历史数据

**检查逻辑：**
1. 查询最近 N 天的交易日（从 `trade_calendar` 表）
2. 查询已有数据的日期（从 `stock_daily` 表，按 `trade_date` 去重）
3. 计算缺失日期：`missing_dates = trading_dates - existing_dates`
4. 如果有缺失，调用 `batch_sync_daily()` 批量补齐

**替代方案：**
- 定时任务补齐：需要额外的定时任务，增加复杂度
- 被动检查：用户发现数据缺失后手动补齐，用户体验差
- 全量检查：检查所有历史数据，启动时间过长

### 4. 数据初始化向导：交互式 CLI 向导

**决策：** 提供交互式 CLI 向导（`scripts/init_data.py`），引导用户选择数据范围并自动初始化。

**理由：**
- **用户友好**：交互式界面，清晰的步骤提示
- **灵活性**：支持 1 年 / 3 年 / 自定义范围
- **安全性**：检测已有数据，提示确认后再执行
- **进度可见**：显示每个步骤的进度和预计剩余时间

**初始化步骤：**
1. 同步股票列表（`sync_stock_list()`）
2. 同步交易日历（`sync_trade_calendar(start_date, end_date)`）
3. 同步日线数据（`batch_sync_daily()` 批量同步）
4. 计算技术指标（`compute_all_stocks()`）

**替代方案：**
- 命令行参数：`--init-data --years 3`，不够友好，容易出错
- Web 界面：需要额外开发前端，增加复杂度
- 自动全量初始化：无法控制数据范围，可能耗时过长

### 5. 优雅关闭：信号处理 + 超时强制停止

**决策：** 监听 SIGTERM/SIGINT 信号，等待运行中的任务完成（最多 30 秒），超时后强制停止。

**理由：**
- **数据一致性**：避免任务中断导致数据不完整
- **可控超时**：30 秒超时避免无限等待
- **标准信号**：SIGTERM 是系统服务停止的标准信号

**实现方式：**
```python
import signal
import asyncio

async def graceful_shutdown():
    # 停止接受新任务
    scheduler.pause()

    # 等待运行中的任务完成（最多 30 秒）
    await asyncio.wait_for(
        wait_for_running_jobs(),
        timeout=30.0
    )

    # 关闭调度器
    scheduler.shutdown()

signal.signal(signal.SIGTERM, lambda s, f: asyncio.create_task(graceful_shutdown()))
```

**替代方案：**
- 立即停止：可能导致数据不完整
- 无限等待：可能导致服务无法停止
- 强制 kill：不优雅，可能导致资源泄漏

## Risks / Trade-offs

### 风险 1：启动时数据补齐耗时过长

**风险：** 如果缺失数据较多（如停机 1 个月），启动时补齐可能需要数小时。

**缓解措施：**
- 默认只检查最近 30 天（可配置）
- 支持 `--skip-integrity-check` 跳过检查，紧急情况下快速启动
- 补齐失败不阻断启动，记录日志后继续启动调度器
- 提供手动补齐命令，用户可以在启动后手动补齐历史数据

### 风险 2：服务管理脚本权限问题

**风险：** Linux 上安装 systemd 服务需要 root 权限，可能导致权限错误。

**缓解措施：**
- 脚本检测权限，提示用户使用 `sudo` 运行
- 提供清晰的错误提示："需要 root 权限，请使用 sudo 运行"
- 文档中明确说明权限要求

### 风险 3：平台兼容性问题

**风险：** systemd 和 launchd 的配置格式和行为差异较大，可能导致兼容性问题。

**缓解措施：**
- 为每个平台提供独立的模板文件
- 充分测试 Linux 和 macOS 两个平台
- 文档中明确说明各平台的差异和注意事项

### 权衡 1：tarball vs Docker

**权衡：** 使用 tarball 而非 Docker，简化部署但失去容器化的隔离性。

**理由：**
- V1 目标是单机部署，不需要容器化的复杂性
- tarball 部署更简单，用户可以直接查看和修改文件
- Docker 可以在 V2 中作为可选的部署方式

### 权衡 2：启动时检查 vs 定时检查

**权衡：** 启动时检查数据完整性，而非定时检查。

**理由：**
- 启动时检查更及时，避免启动后才发现数据缺失
- 定时检查需要额外的定时任务，增加复杂度
- 启动时检查可以通过 `--skip-integrity-check` 跳过，灵活性高

## Migration Plan

### 部署步骤

1. **打包应用**
   ```bash
   python scripts/package.py
   # 生成 dist/stock-selector-<version>.tar.gz
   ```

2. **传输到目标服务器**
   ```bash
   scp dist/stock-selector-<version>.tar.gz user@server:/opt/
   ```

3. **解压并安装依赖**
   ```bash
   cd /opt
   tar -xzf stock-selector-<version>.tar.gz
   cd stock-selector-<version>
   uv sync
   ```

4. **配置环境变量**
   ```bash
   cp .env.example .env
   vim .env  # 修改数据库连接等配置
   ```

5. **初始化数据（首次部署）**
   ```bash
   python scripts/init_data.py
   # 选择数据范围（1 年 / 3 年 / 自定义）
   ```

6. **安装并启动服务**
   ```bash
   sudo python scripts/service.py install
   sudo python scripts/service.py start
   ```

7. **验证服务状态**
   ```bash
   sudo python scripts/service.py status
   ```

### 回滚策略

如果新版本出现问题，回滚步骤：

1. **停止服务**
   ```bash
   sudo python scripts/service.py stop
   ```

2. **切换到旧版本目录**
   ```bash
   cd /opt/stock-selector-<old-version>
   ```

3. **重新安装服务（指向旧版本）**
   ```bash
   sudo python scripts/service.py install
   sudo python scripts/service.py start
   ```

4. **验证服务状态**
   ```bash
   sudo python scripts/service.py status
   ```

### 数据迁移

本次变更不涉及数据库 schema 变更，无需数据迁移。

新增配置项：
- `DATA_INTEGRITY_CHECK_DAYS`（默认 30）
- `DATA_INTEGRITY_CHECK_ENABLED`（默认 true）

## Open Questions

1. **日志轮转策略**：服务日志文件是否需要自动轮转？如何配置轮转策略？
   - 建议：使用 logrotate（Linux）或 newsyslog（macOS）管理日志轮转

2. **多实例部署**：是否需要支持同一台服务器上运行多个实例？
   - 建议：V1 不支持，V2 再考虑（需要端口冲突检测、数据库隔离等）

3. **监控和告警**：是否需要集成监控和告警功能？
   - 建议：V1 不集成，用户可以使用外部监控工具（如 Prometheus + Grafana）

4. **自动更新**：是否需要支持自动更新功能？
   - 建议：V1 不支持，用户手动下载新版本并重新部署
