# P3 指数数据 ETL 实施任务

## 1. DataManager 日常同步方法

- [x] 1.1 在 `app/data/manager.py` 中定义核心指数列表常量 `CORE_INDEX_LIST`
  - 包含上证综指(000001.SH)、深证成指(399001.SZ)、创业板指(399006.SZ)、沪深300(000300.SH)、中证500(000905.SH)、中证1000(000852.SH) 等

- [x] 1.2 在 `app/data/manager.py` 中实现 `sync_raw_index_daily(trade_date)` 方法
  - 遍历 CORE_INDEX_LIST，调用 TushareClient.fetch_raw_index_daily 获取日线行情
  - 使用 _upsert_raw 写入 raw_tushare_index_daily 表
  - 返回 {"index_daily": count}

- [x] 1.3 在 `app/data/manager.py` 中实现 `sync_raw_index_weight(trade_date)` 方法
  - 遍历 CORE_INDEX_LIST，调用 TushareClient.fetch_raw_index_weight 获取成分股权重
  - 使用 _upsert_raw 写入 raw_tushare_index_weight 表
  - 返回 {"index_weight": count}

- [x] 1.4 在 `app/data/manager.py` 中实现 `sync_raw_index_technical(trade_date)` 方法
  - 遍历 CORE_INDEX_LIST，调用 TushareClient.fetch_raw_index_factor_pro 获取技术因子
  - 使用 _upsert_raw 写入 raw_tushare_index_factor_pro 表
  - 返回 {"index_factor_pro": count}

## 2. DataManager 静态数据同步方法

- [x] 2.1 在 `app/data/manager.py` 中实现 `sync_raw_index_basic()` 方法
  - 调用 TushareClient.fetch_raw_index_basic() 获取全部指数基础信息
  - 使用 _upsert_raw 写入 raw_tushare_index_basic 表
  - 返回 {"index_basic": count}

- [x] 2.2 在 `app/data/manager.py` 中实现 `sync_raw_industry_classify()` 方法
  - 调用 TushareClient.fetch_raw_index_classify() 获取行业分类
  - 使用 _upsert_raw 写入 raw_tushare_index_classify 表
  - 返回 {"index_classify": count}

- [x] 2.3 在 `app/data/manager.py` 中实现 `sync_raw_industry_member()` 方法
  - 调用 TushareClient.fetch_raw_index_member_all() 获取行业成分股
  - 使用 _upsert_raw 写入 raw_tushare_index_member_all 表
  - 返回 {"index_member_all": count}

## 3. DataManager ETL 方法

- [x] 3.1 在 `app/data/manager.py` 中实现 `etl_index(trade_date)` 方法
  - 从 raw_tushare_index_daily 读取数据，调用 transform_tushare_index_daily 清洗，写入 index_daily 业务表
  - 从 raw_tushare_index_weight 读取数据，调用 transform_tushare_index_weight 清洗，写入 index_weight 业务表
  - 从 raw_tushare_index_factor_pro 读取数据，调用 transform_tushare_index_technical 清洗，写入 index_technical_daily 业务表
  - 返回 {"index_daily": count, "index_weight": count, "index_technical_daily": count}

- [x] 3.2 在 `app/data/manager.py` 中实现 `etl_index_static()` 方法
  - 从 raw_tushare_index_basic 读取数据，调用 transform_tushare_index_basic 清洗，写入 index_basic 业务表
  - 从 raw_tushare_index_classify 读取数据，调用 transform_tushare_industry_classify 清洗，写入 industry_classify 业务表
  - 从 raw_tushare_index_member_all 读取数据，调用 transform_tushare_industry_member 清洗，写入 industry_member 业务表
  - 返回 {"index_basic": count, "industry_classify": count, "industry_member": count}

## 4. 盘后链路集成

- [x] 4.1 在 `app/scheduler/jobs.py` 的 `run_post_market_chain` 中增加指数数据同步步骤
  - 位置：资金流向同步（步骤 3.5）之后、缓存刷新（步骤 4）之前
  - 调用 sync_raw_index_daily + sync_raw_index_weight + sync_raw_index_technical + etl_index
  - 用 try/except 包裹，失败记录日志但不阻断后续链路

## 5. 导入和注册

- [x] 5.1 在 `app/data/manager.py` 中添加必要的 import
  - Raw 模型：RawTushareIndexBasic, RawTushareIndexDaily, RawTushareIndexWeight, RawTushareIndexClassify, RawTushareIndexMemberAll, RawTushareIndexFactorPro
  - 业务模型：IndexBasic, IndexDaily, IndexWeight, IndustryClassify, IndustryMember, IndexTechnicalDaily
  - ETL 函数：transform_tushare_index_basic, transform_tushare_index_daily, transform_tushare_index_weight, transform_tushare_industry_classify, transform_tushare_industry_member, transform_tushare_index_technical

## 6. 单元测试

- [x] 6.1 在 `tests/unit/test_etl.py` 中添加 transform_tushare_index_daily 测试
  - 测试正常转换、空数据场景

- [x] 6.2 在 `tests/unit/test_etl.py` 中添加 transform_tushare_index_weight 测试
  - 测试正常转换、空数据场景

- [x] 6.3 在 `tests/unit/test_etl.py` 中添加 transform_tushare_index_basic 测试
  - 测试正常转换、空数据场景

- [x] 6.4 在 `tests/unit/test_etl.py` 中添加 transform_tushare_index_technical 测试
  - 测试正常转换、空数据、NaN 字段场景

## 7. 文档更新

- [x] 7.1 更新 `docs/design/99-实施范围-V1与V2划分.md`，将 P3 指数数据标记为"✅ V1 已实施"（含 ETL 和数据同步）
- [x] 7.2 更新 `README.md` 和 `CLAUDE.md`，说明 P3 指数数据 ETL 已完成
- [x] 7.3 更新 `PROJECT_TASKS.md`，标记 p3-index-etl 已完成
