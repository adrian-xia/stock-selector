## Why

系统启动时的 `sync_from_progress` 只同步最近一个交易日的数据，不会补齐中间缺失的天数。如果服务停机数天甚至数周，P0 日线数据会出现缺口，而盘后链路（`run_post_market_chain`）中 P0~P5 各步骤也只处理当天（`mode="incremental"`），不会回溯补齐历史缺口。这导致停机后必须手动执行 `backfill-daily` 或 `init_data` 才能追平数据，运维负担大。

## What Changes

- 改造 `sync_from_progress`（启动同步），增加 P0 多日缺口检测与补齐：利用 `detect_missing_dates` 扫描 `data_start_date` ~ `latest_trade_date` 范围内缺失的交易日，逐日执行 `sync_raw_daily` + `etl_daily`
- 启动同步中增加 P1（财务数据）缺口补齐：检测缺失的报告期并补拉
- 启动同步中增加 P4（板块数据）缺口补齐：检测缺失的板块日线和成分股数据并补拉
- 将启动同步中现有的 P2/P3/P5 `gap_fill` 逻辑统一为完整的 P0~P5 全优先级缺口补齐流程
- 盘后链路中各步骤（P0~P5）增加 `gap_fill` 回溯逻辑：在完成当天 incremental 同步后，检测近 N 天（可配置）的缺口并补齐，防止单日失败导致永久缺口
- 新增配置项控制缺口补齐行为（回溯天数、是否启用等）

## Capabilities

### New Capabilities

- `data-gap-fill`: 统一的数据缺口检测与补齐能力，覆盖 P0~P5 全优先级，适用于启动同步和盘后链路两个场景

### Modified Capabilities

- `scheduler-core`: 启动同步流程变更，从"仅同步最近一天"改为"全量缺口检测 + 逐日补齐"
- `scheduler-jobs`: 盘后链路各步骤增加 gap_fill 回溯逻辑

## Impact

- `app/scheduler/core.py` — `sync_from_progress` 函数重构
- `app/scheduler/jobs.py` — `run_post_market_chain` 各步骤增加回溯补齐
- `app/data/manager.py` — 可能需要新增 P1/P4 的缺口检测方法
- `app/config.py` — 新增 gap_fill 相关配置项（回溯天数、启用开关）
- `.env.example` — 新增配置项说明
