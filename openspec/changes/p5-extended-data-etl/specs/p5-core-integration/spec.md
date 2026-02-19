## MODIFIED Requirements

### Requirement: Integrate extended sync methods into sync_p5_core
The existing sync_p5_core method SHALL be extended to call all 28 new sync_raw_* methods, grouped by frequency.

#### Scenario: Daily frequency sync
- **WHEN** sync_p5_core is called on a trading day
- **THEN** it SHALL call daily-frequency sync methods: hsgt_top10, limit_step, hm_detail, stk_auction, stk_auction_o, kpl_list, kpl_concept, broker_recommend, slb_len, ggt_daily, ccass_hold, ccass_hold_detail, hk_hold, cyq_perf, cyq_chips

#### Scenario: Monthly frequency sync
- **WHEN** sync_p5_core is called on the last trading day of a month
- **THEN** it SHALL additionally call sync_raw_ggt_monthly

#### Scenario: Quarterly/static frequency sync
- **WHEN** sync_p5_core is called on the first trading day of a quarter
- **THEN** it SHALL additionally call static sync methods: namechange, stk_managers, stk_rewards, new_share, stk_list_his, pledge_stat, pledge_detail, repurchase, share_float, report_rc, stk_surv

#### Scenario: Error isolation
- **WHEN** any extended sync method fails
- **THEN** it SHALL log a WARNING and continue with remaining methods, returning partial results
