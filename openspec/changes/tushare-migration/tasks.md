## 1. 基础设施（Phase 0）

- [ ] 1.1 `pyproject.toml` 添加 `tushare>=1.4.0` 依赖，移除 `baostock` 和 `akshare`
- [ ] 1.2 `app/config.py` 添加 Tushare 配置项（tushare_token, tushare_retry_count, tushare_retry_interval, tushare_qps_limit），移除 BaoStock/AKShare 配置项
- [ ] 1.3 `.env.example` 添加 `TUSHARE_TOKEN`，移除 BaoStock/AKShare 相关配置
- [ ] 1.4 创建 `app/data/tushare.py` — TushareClient 基础框架（令牌桶限流 + asyncio.to_thread 异步包装 + 重试机制）
- [ ] 1.5 TushareClient 实现 DataSourceClient Protocol 的 4 个方法（fetch_daily, fetch_stock_list, fetch_trade_calendar, health_check）

## 2. P0 原始表和模型（Phase 1a）

- [ ] 2.1 创建 `app/models/raw.py` — 定义 6 张 P0 原始表模型（raw_tushare_stock_basic, raw_tushare_trade_cal, raw_tushare_daily, raw_tushare_adj_factor, raw_tushare_daily_basic, raw_tushare_stk_limit）
- [ ] 2.2 创建 Alembic 迁移脚本 — P0 原始表建表
- [ ] 2.3 TushareClient 添加 fetch_raw_* 方法（fetch_raw_daily, fetch_raw_adj_factor, fetch_raw_daily_basic, fetch_raw_stk_limit, fetch_raw_stock_basic, fetch_raw_trade_cal）

## 3. P0 ETL 清洗（Phase 1b）

- [ ] 3.1 `app/data/etl.py` 添加 transform_tushare_stock_basic 函数（raw → stocks）
- [ ] 3.2 `app/data/etl.py` 添加 transform_tushare_trade_cal 函数（raw → trade_calendar）
- [ ] 3.3 `app/data/etl.py` 添加 transform_tushare_daily 函数（raw_daily + raw_adj_factor + raw_daily_basic → stock_daily，含 amount 千元→元转换）
- [ ] 3.4 `app/data/etl.py` 移除 clean_baostock_* 和 clean_akshare_* 函数
- [ ] 3.5 `app/data/etl.py` 更新 normalize_stock_code 支持 source="tushare"（直接透传）

## 4. DataManager 改造（Phase 1c）

- [ ] 4.1 `app/data/manager.py` — sync_stock_list() 改用 TushareClient + transform_tushare_stock_basic
- [ ] 4.2 `app/data/manager.py` — sync_trade_calendar() 改用 TushareClient + transform_tushare_trade_cal
- [ ] 4.3 `app/data/manager.py` — 新增 sync_raw_daily(trade_date) 方法（按日期获取全市场 daily+adj_factor+daily_basic 写入 raw 表）
- [ ] 4.4 `app/data/manager.py` — 新增 etl_daily(trade_date) 方法（从 raw 表 JOIN 清洗写入 stock_daily）
- [ ] 4.5 `app/data/manager.py` — 移除 BaoStock/AKShare 相关导入和引用

## 5. 调度器和批量同步改造（Phase 1d）

- [ ] 5.1 `app/data/batch.py` — 重写 batch_sync_daily 为按日期批量模式（逐日 sync_raw_daily + etl_daily）
- [ ] 5.2 `app/scheduler/jobs.py` — _build_manager() 改用 TushareClient
- [ ] 5.3 `app/scheduler/jobs.py` — run_post_market_chain 适配按日期同步模式（sync_raw_daily → etl_daily → 指标计算）
- [ ] 5.4 `app/data/probe.py` — 数据嗅探改用 TushareClient
- [ ] 5.5 删除 `app/data/baostock.py`、`app/data/akshare.py`、`app/data/pool.py`

## 6. P0 验证

- [ ] 6.1 运行现有单元测试，修复因数据源切换导致的失败
- [ ] 6.2 手动验证：stock_basic → raw → stocks 链路
- [ ] 6.3 手动验证：trade_cal → raw → trade_calendar 链路
- [ ] 6.4 手动验证：daily + adj_factor + daily_basic → raw → stock_daily 链路
- [ ] 6.5 手动验证：策略引擎和回测引擎正常工作

## 7. P1 财务数据（Phase 2）

- [ ] 7.1 `app/models/raw.py` 添加 10 张 P1 原始表模型（raw_tushare_fina_indicator, raw_tushare_income, raw_tushare_balancesheet, raw_tushare_cashflow, raw_tushare_dividend, raw_tushare_forecast, raw_tushare_express, raw_tushare_fina_audit, raw_tushare_fina_mainbz, raw_tushare_disclosure_date）
- [ ] 7.2 创建 Alembic 迁移脚本 — P1 原始表建表
- [ ] 7.3 TushareClient 添加财务数据 fetch_raw_* 方法（优先使用 VIP 接口按季度获取全部公司）
- [ ] 7.4 `app/data/etl.py` 添加 transform_tushare_fina_indicator 函数（raw → finance_indicator）
- [ ] 7.5 DataManager 添加 sync_raw_fina(period) 和 etl_fina(period) 方法

## 8. P2 资金流向（Phase 3）

- [ ] 8.1 `app/models/raw.py` 添加 8 张 P2 原始表模型（raw_tushare_moneyflow, raw_tushare_moneyflow_dc, raw_tushare_moneyflow_ths, raw_tushare_moneyflow_hsgt, raw_tushare_moneyflow_ind_ths, raw_tushare_moneyflow_cnt_ths, raw_tushare_moneyflow_ind_dc, raw_tushare_moneyflow_mkt_dc）
- [ ] 8.2 `app/models/raw.py` 添加 2 张龙虎榜原始表模型（raw_tushare_top_list, raw_tushare_top_inst）
- [ ] 8.3 创建 Alembic 迁移脚本 — P2 原始表建表
- [ ] 8.4 TushareClient 添加资金流向和龙虎榜 fetch_raw_* 方法
- [ ] 8.5 `app/data/etl.py` 添加 transform_tushare_moneyflow 和 transform_tushare_top_list 函数
- [ ] 8.6 DataManager 添加 sync_raw_moneyflow(trade_date) 和 etl_moneyflow(trade_date) 方法

## 9. P3 指数数据（Phase 4）

- [ ] 9.1 创建 `app/models/index.py` — 定义 6 张指数业务表模型（index_basic, index_daily, index_weight, industry_classify, industry_member, index_technical_daily）
- [ ] 9.2 `app/models/raw.py` 添加 6 张 P3 原始表模型
- [ ] 9.3 创建 Alembic 迁移脚本 — P3 原始表 + 指数业务表建表（含 index_technical_daily）
- [ ] 9.4 TushareClient 添加指数 fetch_raw_* 方法（index_basic, index_daily, index_weight, index_classify, index_member_all, sw_daily）
- [ ] 9.5 `app/data/etl.py` 添加指数 ETL 清洗函数
- [ ] 9.6 DataManager 添加指数同步方法（sync_index_basic, sync_index_daily, sync_index_weight, sync_industry_classify, sync_industry_member）
- [ ] 9.7 `app/data/indicator.py` 泛化计算函数，支持传入不同的行情表和技术指标表（index_daily → index_technical_daily）
- [ ] 9.8 DataManager 添加 update_index_indicators(trade_date) 方法，基于 index_daily 计算指数技术指标写入 index_technical_daily

## 10. P4 板块数据（Phase 5）

- [ ] 10.1 创建 `app/models/concept.py` — 定义 4 张板块业务表模型（concept_index, concept_daily, concept_member, concept_technical_daily）
- [ ] 10.2 `app/models/raw.py` 添加 8 张 P4 原始表模型
- [ ] 10.3 创建 Alembic 迁移脚本 — P4 原始表 + 板块业务表建表（含 concept_technical_daily）
- [ ] 10.4 TushareClient 添加板块 fetch_raw_* 方法（ths_index, ths_daily, ths_member, dc_index, dc_member, tdx_index, tdx_member, tdx_daily）
- [ ] 10.5 `app/data/etl.py` 添加板块 ETL 清洗函数（统一三个数据源到 concept_* 业务表）
- [ ] 10.6 DataManager 添加板块同步方法（sync_concept_index, sync_concept_daily, sync_concept_member）
- [ ] 10.7 DataManager 添加 update_concept_indicators(trade_date) 方法，基于 concept_daily 计算板块技术指标写入 concept_technical_daily

## 9. P3 指数数据（Phase 4）

- [ ] 9.1 创建 `app/models/index.py` — 定义 6 张指数业务表模型（index_basic, index_daily, index_weight, industry_classify, industry_member, index_technical_daily）
- [ ] 9.2 `app/models/raw.py` 添加 12 张指数原始表模型（raw_tushare_index_basic, raw_tushare_index_weight, raw_tushare_index_daily, raw_tushare_index_weekly, raw_tushare_index_monthly, raw_tushare_index_dailybasic, raw_tushare_index_global, raw_tushare_daily_info, raw_tushare_sz_daily_info, raw_tushare_index_classify, raw_tushare_index_member_all, raw_tushare_sw_daily）
- [ ] 9.3 `app/models/raw.py` 添加 4 张中信行业+指数技术面原始表（raw_tushare_ci_index_member, raw_tushare_ci_daily, raw_tushare_index_factor_pro, raw_tushare_tdx_daily）
- [ ] 9.4 创建 Alembic 迁移脚本 — 指数原始表 + 指数业务表建表（含 index_technical_daily）
- [ ] 9.5 TushareClient 添加指数 fetch_raw_* 方法
- [ ] 9.6 `app/data/etl.py` 添加指数 ETL 清洗函数
- [ ] 9.7 DataManager 添加指数同步方法（sync_index_basic, sync_index_daily, sync_index_weight, sync_industry_classify, sync_industry_member）
- [ ] 9.8 `app/data/indicator.py` 泛化计算函数，支持传入不同的行情表和技术指标表（index_daily → index_technical_daily）
- [ ] 9.9 DataManager 添加 update_index_indicators(trade_date) 方法

## 10. P4 板块数据（Phase 5）

- [ ] 10.1 创建 `app/models/concept.py` — 定义 4 张板块业务表模型（concept_index, concept_daily, concept_member, concept_technical_daily）
- [ ] 10.2 `app/models/raw.py` 添加 8 张板块原始表模型（raw_tushare_ths_index, raw_tushare_ths_daily, raw_tushare_ths_member, raw_tushare_dc_index, raw_tushare_dc_member, raw_tushare_dc_hot_new, raw_tushare_tdx_index, raw_tushare_tdx_member）
- [ ] 10.3 创建 Alembic 迁移脚本 — 板块原始表 + 板块业务表建表（含 concept_technical_daily）
- [ ] 10.4 TushareClient 添加板块 fetch_raw_* 方法
- [ ] 10.5 `app/data/etl.py` 添加板块 ETL 清洗函数（统一三个数据源到 concept_* 业务表）
- [ ] 10.6 DataManager 添加板块同步方法（sync_concept_index, sync_concept_daily, sync_concept_member）
- [ ] 10.7 DataManager 添加 update_concept_indicators(trade_date) 方法

## 11. P5 扩展数据（Phase 6）

### 11a. 基础数据补充（7 张 raw 表）
- [ ] 11.1 `app/models/raw.py` 添加基础数据补充原始表（raw_tushare_namechange, raw_tushare_stock_company, raw_tushare_stk_managers, raw_tushare_stk_rewards, raw_tushare_new_share, raw_tushare_daily_share, raw_tushare_stk_list_his）
- [ ] 11.2 TushareClient 添加对应 fetch_raw_* 方法

### 11b. 行情补充（5 张 raw 表）
- [ ] 11.3 `app/models/raw.py` 添加行情补充原始表（raw_tushare_weekly, raw_tushare_monthly, raw_tushare_suspend_d, raw_tushare_hsgt_top10, raw_tushare_ggt_daily）
- [ ] 11.4 TushareClient 添加对应 fetch_raw_* 方法

### 11c. 市场参考数据（9 张 raw 表）
- [ ] 11.5 `app/models/raw.py` 添加市场参考数据原始表（raw_tushare_top10_holders, raw_tushare_top10_floatholders, raw_tushare_pledge_stat, raw_tushare_pledge_detail, raw_tushare_repurchase, raw_tushare_share_float, raw_tushare_block_trade, raw_tushare_stk_holdernumber, raw_tushare_stk_holdertrade）
- [ ] 11.6 TushareClient 添加对应 fetch_raw_* 方法

### 11d. 特色数据（9 张 raw 表）
- [ ] 11.7 `app/models/raw.py` 添加特色数据原始表（raw_tushare_report_rc, raw_tushare_cyq_perf, raw_tushare_cyq_chips, raw_tushare_stk_factor, raw_tushare_stk_factor_pro, raw_tushare_ccass_hold, raw_tushare_ccass_hold_detail, raw_tushare_hk_hold, raw_tushare_stk_surv）
- [ ] 11.8 TushareClient 添加对应 fetch_raw_* 方法

### 11e. 两融数据（4 张 raw 表）
- [ ] 11.9 `app/models/raw.py` 添加两融原始表（raw_tushare_margin, raw_tushare_margin_detail, raw_tushare_margin_target, raw_tushare_slb_len）
- [ ] 11.10 TushareClient 添加对应 fetch_raw_* 方法

### 11f. 打板专题（14 张 raw 表）
- [ ] 11.11 `app/models/raw.py` 添加打板专题原始表（raw_tushare_limit_list_d, raw_tushare_ths_limit, raw_tushare_limit_step, raw_tushare_hm_board, raw_tushare_hm_list, raw_tushare_hm_detail, raw_tushare_stk_auction, raw_tushare_stk_auction_o, raw_tushare_kpl_list, raw_tushare_kpl_concept, raw_tushare_broker_recommend, raw_tushare_ths_hot, raw_tushare_dc_hot, raw_tushare_ggt_monthly）
- [ ] 11.12 TushareClient 添加对应 fetch_raw_* 方法

### 11g. Alembic 迁移 + ETL
- [ ] 11.13 创建 Alembic 迁移脚本 — P5 全部扩展原始表建表（48 张）
- [ ] 11.14 按需添加 ETL 清洗函数和 DataManager 同步方法

## 12. 数据初始化 CLI（Phase 7）

- [ ] 12.1 更新 `app/data/cli.py` — 新增 init-tushare 命令（全量初始化：stock_basic → trade_cal → 逐日 daily → fina → moneyflow → 指数/板块 → 技术指标）
- [ ] 12.2 新增 `raw_sync_progress` 表追踪原始数据拉取进度，支持断点续传
- [ ] 12.3 更新 `scripts/init_data.py` — 初始化向导改用 Tushare
- [ ] 12.4 盘后链路增量更新集成测试（sync_raw_daily → etl_daily → 指标计算 → 策略执行）

## 13. 文档和清理（Phase 8）

- [ ] 13.1 补全 `docs/tushare/` 下缺失的接口文档（从官网获取指数/板块/扩展接口文档）
- [ ] 13.2 更新 `docs/design/01-详细设计-数据采集.md` — 数据源改为 Tushare，新增 raw 层架构说明
- [ ] 13.3 更新 `docs/design/99-实施范围-V1与V2划分.md` — 标注 Tushare 迁移为已实施
- [ ] 13.4 更新 `README.md` — 技术栈、数据源、配置说明
- [ ] 13.5 更新 `CLAUDE.md` — V1 范围、技术栈、目录结构
- [ ] 13.6 删除 BaoStock/AKShare 相关测试，新增 TushareClient 单元测试
