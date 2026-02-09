## Why

当前的自动数据更新系统（`auto-data-update-system`）在每日盘后链路中不包含交易日历更新，导致系统无法自动获取未来的交易日历数据。虽然周末任务会更新交易日历，但这不够及时，可能导致系统在判断交易日时使用过期的数据。BaoStock API 支持查询未来 90 天的交易日历（基于交易所公布的休市安排），应该在每日盘后链路中更新以保持数据新鲜度。

## What Changes

- 在 `run_post_market_chain()` 函数中添加交易日历更新步骤（作为第一步，在交易日校验之前）
- 交易日历更新失败不阻断后续步骤（记录警告日志并继续）
- 保留周末任务中的交易日历更新（作为兜底机制）
- 添加性能日志记录交易日历更新耗时

## Capabilities

### New Capabilities
<!-- 无新增能力，只是修改现有能力 -->

### Modified Capabilities
- `scheduler-jobs`: 在 `run_post_market_chain()` 中添加交易日历更新步骤，确保每日自动获取未来 90 天的交易日历数据

## Impact

**受影响的代码：**
- `app/scheduler/jobs.py` - 修改 `run_post_market_chain()` 函数，添加交易日历更新步骤
- `app/data/manager.py` - 已有修改（优化交易日历同步逻辑，使用 ON CONFLICT DO UPDATE）
- `app/data/etl.py` - 已有修改（修复 is_open 字段处理）

**受影响的系统：**
- 每日盘后链路执行时间会增加约 1-2 秒（交易日历更新耗时）
- 数据库 `trade_calendar` 表会每日更新（使用 UPSERT，不会产生重复数据）

**依赖：**
- 依赖 BaoStock API 的 `query_trade_dates()` 接口
- 依赖 `app/data/manager.py` 中已实现的 `sync_trade_calendar()` 方法
