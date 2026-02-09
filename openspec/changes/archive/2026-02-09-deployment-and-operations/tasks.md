## 1. 打包脚本实现

- [x] 1.1 创建 `scripts/package.py` 脚本文件
- [x] 1.2 实现版本号获取逻辑（优先使用 git tag，回退到 commit hash）
- [x] 1.3 实现文件收集逻辑（app/, scripts/, templates/, uv.lock, .env.example, README.md）
- [x] 1.4 实现排除规则（排除 tests/, .git/, __pycache__/, *.pyc, .env）
- [x] 1.5 实现包内容验证（检查必需文件：app/main.py, uv.lock, .env.example, README.md）
- [x] 1.6 实现 tarball 打包逻辑（创建 dist/stock-selector-<version>.tar.gz）
- [x] 1.7 添加打包日志输出（版本号、文件数量、包大小）
- [x] 1.8 测试打包脚本（验证生成的包可以正常解压）

## 2. 服务管理脚本实现

- [ ] 2.1 创建 `scripts/service.py` 主脚本（统一接口）
- [ ] 2.2 实现平台检测逻辑（识别 Linux/macOS，不支持 Windows）
- [ ] 2.3 创建 `templates/stock-selector.service` systemd 服务文件模板
- [ ] 2.4 实现 Linux systemd 服务安装逻辑（复制模板到 /etc/systemd/system/，systemctl enable）
- [ ] 2.5 实现 Linux systemd 服务启动/停止逻辑（systemctl start/stop）
- [ ] 2.6 实现 Linux systemd 服务状态查询逻辑（systemctl status）
- [ ] 2.7 实现 Linux systemd 服务卸载逻辑（systemctl stop, systemctl disable, 删除服务文件）
- [ ] 2.8 创建 `templates/com.stock-selector.plist` launchd plist 文件模板
- [ ] 2.9 实现 macOS launchd 服务安装逻辑（复制模板到 ~/Library/LaunchAgents/，launchctl load）
- [ ] 2.10 实现 macOS launchd 服务启动/停止逻辑（launchctl start/stop）
- [ ] 2.11 实现 macOS launchd 服务状态查询逻辑（launchctl list | grep）
- [ ] 2.12 实现 macOS launchd 服务卸载逻辑（launchctl unload, 删除 plist 文件）
- [ ] 2.13 实现前台启动模式（--foreground 参数，直接运行 uvicorn，日志输出到 stdout）
- [ ] 2.14 实现权限检测（Linux 安装需要 root 权限，提示使用 sudo）
- [ ] 2.15 测试服务管理脚本（在 Linux/macOS 上测试安装、启动、停止、卸载）

## 3. 优雅关闭实现

- [x] 3.1 在 `app/main.py` 添加信号处理器（监听 SIGTERM 和 SIGINT）
- [x] 3.2 实现优雅关闭逻辑（停止接受新任务，等待运行中的任务完成）
- [x] 3.3 实现超时强制停止（30 秒超时后强制关闭）
- [x] 3.4 添加关闭日志（记录关闭开始、等待任务、关闭完成）
- [x] 3.5 测试优雅关闭（验证任务完成后再停止，超时后强制停止）

## 4. 数据完整性检查实现

- [x] 4.1 在 `app/data/manager.py` 添加 `detect_missing_dates()` 方法
- [x] 4.2 实现交易日查询逻辑（查询指定日期范围的交易日）
- [x] 4.3 实现已有数据查询逻辑（查询 stock_daily 表中已有数据的日期，按 trade_date 去重）
- [x] 4.4 实现缺失日期计算逻辑（交易日 - 已有日期）
- [x] 4.5 添加 `detect_missing_dates()` 单元测试（测试无缺失、部分缺失、全部缺失场景）

## 5. 启动时数据完整性检查

- [x] 5.1 在 `app/scheduler/core.py` 添加启动时数据完整性检查函数
- [x] 5.2 实现检查逻辑（检查最近 N 天，调用 detect_missing_dates()）
- [x] 5.3 实现自动补齐逻辑（如果有缺失，调用 batch_sync_daily 补齐）
- [x] 5.4 添加检查日志（记录检查窗口、缺失日期数量、补齐进度）
- [x] 5.5 实现 `--skip-integrity-check` 命令行参数（跳过检查）
- [x] 5.6 在 `app/config.py` 添加 `DATA_INTEGRITY_CHECK_DAYS` 配置项（默认 30）
- [x] 5.7 在 `app/config.py` 添加 `DATA_INTEGRITY_CHECK_ENABLED` 配置项（默认 true）
- [x] 5.8 在 `.env.example` 添加数据完整性检查配置说明
- [x] 5.9 测试启动时检查（模拟缺失数据场景，验证自动补齐）

## 6. 手动数据补齐命令

- [x] 6.1 在 `app/data/cli.py` 添加 `backfill-daily` 命令
- [x] 6.2 实现日期范围参数解析（--start, --end）
- [x] 6.3 实现交易日过滤逻辑（调用 get_trade_calendar，只补齐交易日）
- [x] 6.4 实现已有数据检查逻辑（调用 detect_missing_dates，跳过已有数据的日期）
- [x] 6.5 实现批量补齐逻辑（调用 batch_sync_daily）
- [x] 6.6 添加进度日志（显示补齐进度和预计剩余时间）
- [x] 6.7 添加 `--rate-limit` 参数（降低补齐速度，避免 API 限流）
- [x] 6.8 测试补齐命令（验证跳过已有数据、只补齐缺失数据、速率限制）

## 7. 数据初始化向导实现

- [x] 7.1 创建 `scripts/init_data.py` 初始化向导脚本
- [x] 7.2 实现数据库状态检测（检查 stock_daily 表是否已有数据）
- [x] 7.3 实现交互式选项（1 年 / 3 年 / 自定义范围，使用 input() 获取用户输入）
- [x] 7.4 实现日期范围计算（1 年 ≈ 250 交易日，3 年 ≈ 750 交易日）
- [x] 7.5 实现初始化流程编排（步骤 1: 股票列表 → 步骤 2: 交易日历 → 步骤 3: 日线数据 → 步骤 4: 技术指标）
- [x] 7.6 实现步骤 1：同步股票列表（调用 manager.sync_stock_list()）
- [x] 7.7 实现步骤 2：同步交易日历（调用 manager.sync_trade_calendar(start_date, end_date)）
- [x] 7.8 实现步骤 3：同步日线数据（调用 batch_sync_daily，显示进度）
- [x] 7.9 实现步骤 4：计算技术指标（调用 compute_all_stocks，显示进度）
- [x] 7.10 添加进度显示（每 1000 只股票显示一次进度和预计剩余时间）
- [x] 7.11 添加确认提示（数据库已有数据时提示是否继续）
- [x] 7.12 添加大数据范围警告（自定义范围 >5 年时提示可能耗时数小时）
- [x] 7.13 测试初始化向导（验证完整的初始化流程，测试各种数据范围选项）

## 8. 文档更新

- [x] 8.1 更新 `README.md` 添加"部署"章节（打包、传输、解压、配置）
- [x] 8.2 更新 `README.md` 添加"服务管理"章节（安装服务、启动、停止、状态查询、卸载）
- [x] 8.3 更新 `README.md` 添加"数据初始化"章节（初始化向导、手动补齐命令）
- [x] 8.4 更新 `README.md` 添加"数据完整性检查"章节（启动时检查、配置选项）
- [x] 8.5 更新 `CLAUDE.md` 补充部署和运维相关说明
- [x] 8.6 更新 `.env.example` 确保包含所有新配置项（DATA_INTEGRITY_CHECK_DAYS, DATA_INTEGRITY_CHECK_ENABLED）

## 9. 测试和验证

- [x] 9.1 测试打包流程（打包 → 解压 → 验证文件完整性）
- [ ] 9.2 测试 Linux 服务管理（安装 → 启动 → 状态查询 → 停止 → 卸载）
- [ ] 9.3 测试 macOS 服务管理（安装 → 启动 → 状态查询 → 停止 → 卸载）
- [x] 9.4 测试前台启动模式（验证日志输出到 stdout）
- [x] 9.5 测试优雅关闭（验证任务完成后再停止，超时后强制停止）
- [x] 9.6 测试启动时数据完整性检查（模拟缺失数据，验证自动补齐）
- [x] 9.7 测试 --skip-integrity-check 参数（验证跳过检查）
- [x] 9.8 测试手动补齐命令（指定日期范围、验证跳过已有数据）
- [x] 9.9 测试数据初始化向导（1 年 / 3 年 / 自定义范围）
- [ ] 9.10 测试完整部署流程（打包 → 传输 → 解压 → 配置 → 初始化 → 安装服务 → 启动）
- [x] 9.11 验证日志输出（确保所有关键步骤都有日志记录）
- [x] 9.12 验证错误处理（测试各种异常场景，确保错误提示清晰）
