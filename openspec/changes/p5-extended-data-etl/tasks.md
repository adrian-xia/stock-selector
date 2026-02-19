## 1. 基础补充表同步（5 张）

- [x] 1.1 在 `app/data/manager.py` 新增 `sync_raw_namechange` 方法
- [x] 1.2 新增 `sync_raw_stk_managers` 方法
- [x] 1.3 新增 `sync_raw_stk_rewards` 方法
- [x] 1.4 新增 `sync_raw_new_share` 方法
- [x] 1.5 新增 `sync_raw_stk_list_his` 方法

## 2. 行情补充表同步（2 张）

- [x] 2.1 新增 `sync_raw_hsgt_top10` 方法
- [x] 2.2 新增 `sync_raw_ggt_daily` 方法

## 3. 市场参考表同步（4 张）

- [x] 3.1 新增 `sync_raw_pledge_stat` 方法
- [x] 3.2 新增 `sync_raw_pledge_detail` 方法
- [x] 3.3 新增 `sync_raw_repurchase` 方法
- [x] 3.4 新增 `sync_raw_share_float` 方法

## 4. 特色数据表同步（7 张）

- [x] 4.1 新增 `sync_raw_report_rc` 方法
- [x] 4.2 新增 `sync_raw_cyq_perf` 方法
- [x] 4.3 新增 `sync_raw_cyq_chips` 方法
- [x] 4.4 新增 `sync_raw_ccass_hold` 方法
- [x] 4.5 新增 `sync_raw_ccass_hold_detail` 方法
- [x] 4.6 新增 `sync_raw_hk_hold` 方法
- [x] 4.7 新增 `sync_raw_stk_surv` 方法

## 5. 两融补充表同步（1 张）

- [x] 5.1 新增 `sync_raw_slb_len` 方法

## 6. 打板专题表同步（9 张）

- [x] 6.1 新增 `sync_raw_limit_step` 方法
- [x] 6.2 新增 `sync_raw_hm_detail` 方法
- [x] 6.3 新增 `sync_raw_stk_auction` 方法
- [x] 6.4 新增 `sync_raw_stk_auction_o` 方法
- [x] 6.5 新增 `sync_raw_kpl_list` 方法
- [x] 6.6 新增 `sync_raw_kpl_concept` 方法
- [x] 6.7 新增 `sync_raw_broker_recommend` 方法
- [x] 6.8 新增 `sync_raw_ggt_monthly` 方法

## 7. sync_p5_core 集成

- [x] 7.1 在 `sync_p5_core` 中集成日频补充表同步（15 张）
- [x] 7.2 在 `sync_p5_core` 中集成月频补充表同步（ggt_monthly）
- [x] 7.3 在 `sync_p5_core` 中集成静态/低频补充表同步（12 张，每季度首个交易日）

## 8. 单元测试

- [x] 8.1 创建 `tests/unit/test_p5_extended_sync.py`，测试 28 个 sync_raw_* 方法（mock TushareClient）
- [x] 8.2 测试 sync_p5_core 集成逻辑（频率分组、错误隔离）

## 9. 文档更新

- [x] 9.1 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注 P5 补充数据已实施
- [x] 9.2 更新 `README.md`
- [x] 9.3 更新 `CLAUDE.md`
- [x] 9.4 更新 `PROJECT_TASKS.md`，标记 Change 11 为已完成
