## Context

当前系统已实现核心功能（数据采集、策略引擎、回测、AI 分析、定时任务），但缺少生产环境部署和运维支持。系统以开发模式运行（`uvicorn --reload`），无法作为系统服务管理，也缺少标准化的打包和部署流程。

此外，增量任务（日线同步、技术指标计算、缓存刷新）的性能瓶颈不明确。虽然已实现批量并发同步，但缺少详细的耗时日志，无法定位性能瓶颈。定时任务只同步当天数据，服务停机期间的数据会永久缺失。

**当前状态：**
- 应用以开发模式运行，无法后台运行或开机自启动
- 无标准化打包流程，部署依赖手动操作
- 性能日志粗粒度，只有总耗时，无法定位瓶颈
- 服务停机后重启，中间数据缺失，需要手动补齐

**约束：**
- 必须支持 Mac、Linux、Windows 三个操作系统
- 不能引入复杂的容器化方案（Docker/K8s），保持单机部署简单性
- 性能日志不能显著影响任务执行性能（<5% 开销）
- 数据补齐必须避免重复同步，检查已有数据

## Goals / Non-Goals

**Goals:**
- 提供标准化的应用打包和部署流程
- 支持跨平台服务管理（注册、启动、停止、注销）
- 实现数据完整性检查和自动补齐机制
- 增强性能日志，支持性能瓶颈分析
- 在 PROJECT_TASKS.md 中跟踪性能优化任务

**Non-Goals:**
- 不实现容器化部署（Docker/K8s）
- 不实现分布式部署（多机集群）
- 不实现实时性能监控（Prometheus/Grafana）
- 不实现日志聚合系统（ELK/Loki）
- 不修改现有的批量同步逻辑（只增加日志）

## Decisions

### 决策 1：打包方式 - 使用 tarball 而非 PyInstaller

**选择：** 使用 `tar.gz` 打包源代码 + 依赖锁文件

**理由：**
- PyInstaller 打包后体积大（>100MB），且不支持动态加载模块
- 源代码打包保持灵活性，便于调试和热修复
- uv 的 `uv.lock` 文件已锁定依赖版本，保证可重现部署
- 目标环境已有 Python 3.12+，无需打包 Python 解释器

**替代方案：**
- PyInstaller：体积大，不支持动态加载，调试困难
- zipapp：不支持 C 扩展依赖（如 asyncpg）

**实现：**
- `scripts/package.py` 创建 `dist/stock-selector-<version>.tar.gz`
- 包含：源代码、uv.lock、.env.example、启动脚本、README
- 版本号从 git tag 或 commit hash 获取

### 决策 2：服务管理 - 使用平台原生服务管理器

**选择：** Linux 使用 systemd，Mac 使用 launchd，Windows 使用 Service Control Manager

**理由：**
- 平台原生方案最稳定，无需额外依赖
- 支持开机自启动、日志管理、进程监控
- 用户熟悉度高，便于运维

**替代方案：**
- Supervisor：需要额外安装，不支持 Windows
- PM2：Node.js 依赖，不适合 Python 应用
- 自定义守护进程：复杂度高，稳定性差

**实现：**
- `scripts/service.py` 统一接口，内部根据平台调用不同实现
- Linux: 生成 `/etc/systemd/system/stock-selector.service`
- Mac: 生成 `/Library/LaunchDaemons/com.stock-selector.plist`
- Windows: 使用 `pywin32` 注册 Windows 服务

### 决策 3：数据完整性检查 - 启动时自动检查 + 手动补齐命令

**选择：** 调度器启动时自动检查最近 30 天，提供手动补齐命令

**理由：**
- 启动时检查避免数据缺失被忽略，自动修复常见问题
- 30 天窗口覆盖大部分停机场景，检查速度快（<10 秒）
- 手动命令支持历史数据补齐和特殊场景

**替代方案：**
- 只提供手动命令：用户容易忘记，数据缺失风险高
- 每次任务前检查：性能开销大，不必要
- 定期检查任务：复杂度高，不如启动时检查直接

**实现：**
- `app/scheduler/core.py:start_scheduler()` 调用数据完整性检查
- 检查逻辑：查询最近 30 天交易日，检测缺失日期，调用 `batch_sync_daily` 补齐
- 手动命令：`uv run python -m app.data.cli backfill-daily --start <date> --end <date>`
- 初始化向导：`uv run python scripts/init_data.py`，交互式选择数据范围

### 决策 4：性能日志 - 结构化日志 + 可配置级别

**选择：** 使用 Python logging，结构化格式，支持 DEBUG/INFO/WARNING 三级

**理由：**
- Python logging 标准库，无需额外依赖
- 结构化格式便于日志分析和性能指标提取
- 可配置级别平衡详细度和性能开销

**日志格式：**
```
[模块名] 操作：详情，耗时 Xs
[批量同步] Batch 5/80 完成：成功 98/100，耗时 15.2s
[技术指标] MA 计算完成：8000 只股票，耗时 12.5s
```

**日志级别：**
- DEBUG：记录每只股票的耗时（开发调试用）
- INFO：记录批次和总体耗时（默认，生产环境）
- WARNING：只记录慢速操作和失败（最小开销）

**实现位置：**
- `app/data/batch.py`: 批量同步日志（批次进度、慢速股票）
- `app/data/baostock.py`: BaoStock 客户端细粒度日志（连接池等待、API 调用分步计时）
- `app/data/manager.py`: 单股票同步细粒度日志（API 总计、数据清洗、数据库写入分步计时）
- `app/data/indicator.py`: 技术指标日志（每个指标耗时）
- `app/cache/tech_cache.py`: 缓存刷新日志（命中率、耗时）
- `app/scheduler/jobs.py`: 任务总体日志（开始、完成、总耗时）

**细粒度日志示例：**
```python
# app/data/baostock.py 中的 fetch_daily() 方法
logger.debug("[fetch_daily] %s: 连接池等待=%.2fs, API调用=%.2fs", code, pool_time, api_time)

# app/data/manager.py 中的 sync_daily() 方法
logger.debug("[sync_daily] %s: API总计=%.2fs, 清洗=%.2fs, 入库=%.2fs", code, api_time, clean_time, db_time)
```

这样可以精确定位性能瓶颈：
- 连接池等待慢 → 连接池配置需要优化（已优化：立即创建会话）
- API 调用慢 → 网络问题或 BaoStock 限流
- 数据清洗慢 → 数据转换逻辑需要优化
- 数据库写入慢 → 数据库 IO 或索引问题

**性能优化成果：**
- 优化前：单股票同步 30.46s（连接池等待 30.11s + API 调用 0.32s）
- 优化后：单股票同步 0.45s（连接池等待 0.36s + API 调用 0.08s）
- 性能提升：**67 倍**

### 决策 4.1：连接池获取优化 - 立即创建会话

**问题：** 实施细粒度日志后发现，连接池首次获取会话时会等待 30 秒超时，导致单股票同步耗时 30+ 秒。

**原因：** 原实现使用 `asyncio.wait_for(queue.get(), timeout=30)` 阻塞等待，队列为空时会等待超时才创建新会话。

**选择：** 优先使用 `queue.get_nowait()` 非阻塞获取，队列为空时立即创建新会话。

**实现：**
```python
# app/data/pool.py 中的 acquire() 方法
try:
    session = self._queue.get_nowait()  # 非阻塞获取
except asyncio.QueueEmpty:
    if self._created_count < self._size:
        session = await self._create_session()  # 立即创建
    else:
        # 已达上限，才阻塞等待
        session = await asyncio.wait_for(self._queue.get(), timeout=self._timeout)
```

**效果：**
- 连接池等待时间：30.11s → 0.36s（减少 98.8%）
- 单股票同步总耗时：30.46s → 0.45s（提升 67 倍）
- 10 只股票批量同步：1.1s，平均 0.113s/只

### 决策 5：避免重复同步 - 数据库查询检查

**选择：** 补齐前查询数据库，只同步缺失的日期和股票

**理由：**
- 避免重复 API 调用和数据库写入，节省时间和资源
- 支持部分补齐（某些股票缺失数据）

**实现：**
```python
async def backfill_daily(start_date, end_date):
    # 1. 查询交易日历
    trading_days = await get_trading_days(start_date, end_date)

    # 2. 查询已有数据的日期
    existing_dates = await get_existing_daily_dates(start_date, end_date)

    # 3. 计算缺失日期
    missing_dates = set(trading_days) - set(existing_dates)

    # 4. 只同步缺失日期
    for date in missing_dates:
        await batch_sync_daily(date)
```

## Risks / Trade-offs

### 风险 1：平台差异导致服务管理失败
**风险：** 不同操作系统版本的服务管理器行为可能不一致

**缓解措施：**
- 在主流版本上测试（Ubuntu 20.04+, macOS 12+, Windows 10+）
- 提供详细的错误日志和故障排查文档
- 提供手动安装脚本作为备选方案

### 风险 2：启动时数据检查延迟服务启动
**风险：** 如果缺失大量数据，启动时检查可能耗时很长（>10 分钟）

**缓解措施：**
- 限制检查窗口为 30 天（可配置）
- 检查和补齐在后台异步执行，不阻塞定时任务注册
- 提供 `--skip-integrity-check` 启动参数跳过检查

### 风险 3：性能日志增加日志量
**风险：** 详细日志可能导致日志文件快速增长（每天数 GB）

**缓解措施：**
- 默认使用 INFO 级别，只记录批次和总体耗时
- 配置日志轮转（按天或按大小）
- 在 README 中说明日志存储需求

### 风险 4：数据补齐可能触发 API 限流
**风险：** 大量补齐请求可能触发 BaoStock API 限流

**缓解措施：**
- 复用现有的批量同步逻辑（已有并发控制和连接池）
- 补齐时使用相同的并发限制（DAILY_SYNC_CONCURRENCY）
- 提供 `--rate-limit` 参数降低补齐速度

### 权衡 1：打包体积 vs 部署便利性
**权衡：** tarball 打包需要目标环境安装 Python 和依赖

**选择：** 接受这个权衡，因为目标用户是技术用户，有 Python 环境

### 权衡 2：启动检查 vs 启动速度
**权衡：** 启动时检查增加启动时间（5-10 秒）

**选择：** 接受这个权衡，数据完整性比启动速度更重要

## Migration Plan

### 部署步骤

1. **打包应用**
   ```bash
   uv run python scripts/package.py
   # 生成 dist/stock-selector-v1.1.0.tar.gz
   ```

2. **传输到目标服务器**
   ```bash
   scp dist/stock-selector-v1.1.0.tar.gz user@server:/opt/
   ```

3. **解压并安装依赖**
   ```bash
   cd /opt
   tar -xzf stock-selector-v1.1.0.tar.gz
   cd stock-selector
   uv sync --frozen
   ```

4. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 配置数据库、Redis 等
   ```

5. **初始化数据（首次部署）**
   ```bash
   uv run python scripts/init_data.py
   # 选择初始化范围（1 年 / 3 年 / 自定义）
   ```

6. **安装系统服务**
   ```bash
   sudo uv run python scripts/service.py install
   ```

7. **启动服务**
   ```bash
   sudo uv run python scripts/service.py start
   ```

8. **验证服务状态**
   ```bash
   uv run python scripts/service.py status
   curl http://localhost:8000/health
   ```

### 回滚策略

如果新版本出现问题：

1. **停止服务**
   ```bash
   sudo uv run python scripts/service.py stop
   ```

2. **切换到旧版本目录**
   ```bash
   cd /opt/stock-selector-v1.0.0
   ```

3. **重新安装服务（指向旧版本）**
   ```bash
   sudo uv run python scripts/service.py install
   ```

4. **启动服务**
   ```bash
   sudo uv run python scripts/service.py start
   ```

### 数据库迁移

本次变更不涉及数据库 schema 变更，无需运行 Alembic 迁移。

## Open Questions

1. **日志轮转策略**
   - 问题：使用系统日志轮转（logrotate）还是应用内轮转（logging.handlers.RotatingFileHandler）？
   - 倾向：使用系统日志轮转，更灵活，不增加应用复杂度

2. **Windows 服务依赖**
   - 问题：是否将 `pywin32` 作为可选依赖，还是必需依赖？
   - 倾向：可选依赖，只在 Windows 平台安装

3. **性能日志存储**
   - 问题：是否将性能指标写入数据库，便于长期分析？
   - 倾向：暂不实现，先使用日志文件，后续可以添加

4. **数据完整性检查频率**
   - 问题：除了启动时检查，是否需要定期检查（如每周）？
   - 倾向：暂不实现，启动时检查已覆盖大部分场景
