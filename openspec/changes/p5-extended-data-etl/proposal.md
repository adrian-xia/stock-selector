## Why

P5 核心已实施 20 张 raw 表的数据同步和 2 个 ETL（suspend_d → suspend_info, limit_list_d → limit_list_daily），但剩余 28 张补充表尚未接入同步链路。这些表包含股东数据、质押信息、两融数据、筹码分布等重要维度，补全后可为后续策略扩展和数据分析提供更完整的数据基础。

## What Changes

- **新增 28 个 sync_raw_* 方法**：在 DataManager 中为剩余 P5 补充表添加数据同步方法
  - 基础补充（5 张）：namechange, stk_managers, stk_rewards, new_share, stk_list_his
  - 行情补充（2 张）：hsgt_top10, ggt_daily
  - 市场参考（4 张）：pledge_stat, pledge_detail, repurchase, share_float
  - 特色数据（7 张）：report_rc, cyq_perf, cyq_chips, ccass_hold, ccass_hold_detail, hk_hold, stk_surv
  - 两融补充（1 张）：slb_len
  - 打板专题（9 张）：limit_step, hm_detail, stk_auction, stk_auction_o, kpl_list, kpl_concept, broker_recommend, ggt_monthly
- **扩展 sync_p5_core**：将新增的 sync_raw_* 方法按频率分组集成到 sync_p5_core 聚合入口
- **TushareClient fetch_raw_* 方法**：已全部实现，无需新增
- **不新增业务表**：补充表数据直接从 raw 表查询，不需要 ETL 到业务表

## Out of Scope

- 不新增业务表或 ETL 清洗函数（补充表直接查询 raw 表即可）
- 不修改盘后链路（sync_p5_core 已在步骤 3.8 中调用）
- 不新增前端页面
