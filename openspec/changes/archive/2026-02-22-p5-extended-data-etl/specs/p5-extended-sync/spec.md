## ADDED Requirements

### Requirement: Sync basic supplementary tables
The system SHALL provide sync_raw_* methods for 5 basic supplementary tables: namechange, stk_managers, stk_rewards, new_share, stk_list_his.

#### Scenario: Sync namechange data
- **WHEN** sync_raw_namechange is called with a trade_date
- **THEN** it SHALL fetch data from TushareClient.fetch_raw_namechange and upsert into raw_tushare_namechange table

#### Scenario: Sync stk_managers data
- **WHEN** sync_raw_stk_managers is called
- **THEN** it SHALL fetch and upsert into raw_tushare_stk_managers table

---

### Requirement: Sync market quote supplementary tables
The system SHALL provide sync_raw_* methods for 2 quote supplementary tables: hsgt_top10, ggt_daily.

#### Scenario: Sync hsgt_top10 data
- **WHEN** sync_raw_hsgt_top10 is called with a trade_date
- **THEN** it SHALL fetch northbound top 10 trading data and upsert into raw_tushare_hsgt_top10

---

### Requirement: Sync market reference tables
The system SHALL provide sync_raw_* methods for 4 market reference tables: pledge_stat, pledge_detail, repurchase, share_float.

#### Scenario: Sync pledge_stat data
- **WHEN** sync_raw_pledge_stat is called
- **THEN** it SHALL fetch equity pledge statistics and upsert into raw_tushare_pledge_stat

---

### Requirement: Sync specialty data tables
The system SHALL provide sync_raw_* methods for 7 specialty tables: report_rc, cyq_perf, cyq_chips, ccass_hold, ccass_hold_detail, hk_hold, stk_surv.

#### Scenario: Sync cyq_perf data
- **WHEN** sync_raw_cyq_perf is called with a trade_date
- **THEN** it SHALL fetch chip distribution performance data and upsert into raw_tushare_cyq_perf

---

### Requirement: Sync margin supplementary table
The system SHALL provide sync_raw_slb_len method for securities lending data.

#### Scenario: Sync slb_len data
- **WHEN** sync_raw_slb_len is called with a trade_date
- **THEN** it SHALL fetch securities lending data and upsert into raw_tushare_slb_len

---

### Requirement: Sync board-hitting specialty tables
The system SHALL provide sync_raw_* methods for 9 board-hitting tables: limit_step, hm_detail, stk_auction, stk_auction_o, kpl_list, kpl_concept, broker_recommend, ggt_monthly.

#### Scenario: Sync limit_step data
- **WHEN** sync_raw_limit_step is called with a trade_date
- **THEN** it SHALL fetch limit step data and upsert into raw_tushare_limit_step

#### Scenario: Individual table failure
- **WHEN** any single sync_raw_* method fails
- **THEN** it SHALL log a WARNING and not affect other tables
