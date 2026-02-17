# P4 板块数据 ETL 实施任务

## 1. 盘后链路集成

- [x] 1.1 在 `app/scheduler/jobs.py` 的 `run_post_market_chain` 中增加板块数据同步步骤
  - 位置：指数数据同步（步骤 3.6）之后、缓存刷新（步骤 4）之前
  - 调用 sync_concept_daily 同步同花顺板块日线行情
  - 调用 update_concept_indicators 计算板块技术指标
  - 用 try/except 包裹，失败记录日志但不阻断后续链路

## 2. 单元测试

- [x] 2.1 在 `tests/unit/test_etl.py` 中添加 transform_tushare_concept_index 测试
  - 测试正常转换（含 src 参数）、空数据场景

- [x] 2.2 在 `tests/unit/test_etl.py` 中添加 transform_tushare_concept_daily 测试
  - 测试正常转换、空数据场景

- [x] 2.3 在 `tests/unit/test_etl.py` 中添加 transform_tushare_concept_member 测试
  - 测试正常转换、空数据场景

## 3. 文档更新

- [x] 3.1 更新 `docs/design/99-实施范围-V1与V2划分.md`，将 P4 板块数据标记为"✅ V1 已实施"（含 ETL、数据同步和盘后链路集成）
- [x] 3.2 更新 `README.md` 和 `CLAUDE.md`，说明 P4 板块数据 ETL 已完成
- [x] 3.3 更新 `PROJECT_TASKS.md`，标记 p4-concept-etl 已完成
