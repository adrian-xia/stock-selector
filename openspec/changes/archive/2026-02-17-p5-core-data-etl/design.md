## Context

P5 扩展数据共 48 张 raw 表，ORM 模型和 TushareClient fetch 方法已全部实现（仅建表状态）。P0-P4 的 ETL 模式已成熟：raw 同步 → ETL 清洗 → 盘后链路集成。本次 Change 4 聚焦约 20 张核心表，剩余 28 张留给 Change 11。

现有基础设施：
- `_upsert_raw` 通用方法：自动检测主键、ON CONFLICT DO UPDATE、自动分批
- `transform_tushare_*` ETL 函数：parse_date / parse_decimal / _safe_str 工具链
- 盘后链路：步骤 3.5（P2）→ 3.6（P3）→ 3.7（P4），P5 顺延为 3.8

## Goals / Non-Goals

**Goals:**
- 实现约 20 张 P5 核心 raw 表的数据同步（DataManager sync_raw 方法）
- 为停复牌和涨跌停统计创建业务表及 ETL 清洗
- 集成到盘后链路步骤 3.8，按同步频率分组调度
- 复用已有 ETL 模式，保持代码风格一致

**Non-Goals:**
- 不实现剩余 28 张 P5 补充表（Change 11 范围）
- 不为大部分 raw 表创建业务表（直接查询 raw 表即可）
- 不修改现有 P0-P4 的同步逻辑
- 不新增外部依赖

## Decisions

### Decision 1: 仅停复牌和涨跌停创建业务表

**选择**：仅为 suspend_d 和 limit_list_d 创建业务表，其余约 18 张表直接查询 raw 表。

**理由**：
- 停复牌：策略引擎需要快速判断股票是否停牌，需要标准化的 date 类型字段
- 涨跌停：打板策略核心数据，需要标准化日期和 Decimal 类型
- 其余表：当前无策略直接依赖，raw 表数据格式已足够查询使用
- 减少维护成本，后续按需再添加业务表

**替代方案**：为所有表创建业务表 → 工作量大且大部分无实际消费者

### Decision 2: 按同步频率分组调度

**选择**：在 sync_p5_core 聚合方法中按频率分组，盘后链路每日调用时内部判断是否需要执行周频/月频/静态数据。

**理由**：
- 日频数据（13 张表）：每个交易日执行
- 周频数据（weekly）：仅周五执行
- 月频数据（monthly）：仅月末最后一个交易日执行
- 静态数据（stock_company 等 6 张表）：首次全量 + 每季度更新

**替代方案**：为不同频率注册独立的 APScheduler 任务 → 增加调度复杂度，不如在聚合方法内判断

### Decision 3: P5 同步失败不阻断盘后链路

**选择**：步骤 3.8 整体 try/except，失败记录日志但不阻断后续步骤（缓存刷新、策略执行）。

**理由**：与 P2/P3/P4 保持一致的容错策略，P5 数据为增强数据，非核心链路必需。

### Decision 4: 业务表命名和结构

**选择**：
- `suspend_info` 表：ts_code, trade_date, suspend_type, suspend_timing（停牌类型和时间）
- `limit_list_daily` 表：ts_code, trade_date, limit（U/D/Z）, pct_chg, amp, fc_ratio, fl_ratio, fd_amount, first_time, last_time, open_times, strth, limit_amount

**理由**：字段从 raw 表直接映射，仅做日期格式转换和数值类型标准化。

## Risks / Trade-offs

- [约 20 个 sync_raw 方法代码重复度高] → 每个方法仅 3-5 行，调用 fetch + _upsert_raw，重复可接受；可考虑批量生成但增加复杂度
- [日频 13 张表串行同步耗时] → 单次 API 调用耗时约 1-3 秒，13 张表约 15-40 秒，可接受；后续可改为并发
- [Tushare API 限流] → 复用已有令牌桶限流（400 QPS），P5 日频仅增加约 13 次调用，不会触发限流
- [部分接口可能无数据] → 某些低频接口（如 stk_holdertrade）可能返回空数据，sync_raw 方法需正确处理空结果
