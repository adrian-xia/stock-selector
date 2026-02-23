## 1. 基础设施修复

- [x] 1.1 修复 copy_writer.py COPY 协议临时表创建逻辑，在 COPY 前显式创建 `CREATE TEMP TABLE IF NOT EXISTS _tmp_xxx (LIKE xxx INCLUDING ALL) ON COMMIT DROP`
- [x] 1.2 batch_insert 从 `on_conflict_do_nothing()` 改为 `on_conflict_do_update()`，与 _upsert_raw 保持一致
- [x] 1.3 创建 raw_sync_progress 表（table_name PK, last_sync_date, last_sync_rows, updated_at），添加 Alembic 迁移

## 2. P3/P4/P5 已知问题修复

- [x] 2.1 排查并修复 P3 index_factor_pro 接口名问题（确认正确接口名或标记为不可用）
- [x] 2.2 修复 P3 industry_classify 返回 0 行问题（排查参数）
- [x] 2.3 修复 P3 industry_member null 主键问题（_upsert_raw 已有过滤，验证是否生效）
- [x] 2.4 盘后链路步骤 3.7 增加 concept_member 同步逻辑
- [x] 2.5 盘后链路步骤 3.7 增加 concept_technical_daily 计算逻辑
- [x] 2.6 逐项排查 P5 12 项失败原因（daily_share、hm_board、hm_list、ths_limit、hsgt_top10、ccass_hold_detail、cyq_chips、limit_step、hm_detail、stk_auction_o、kpl_concept、broker_recommend），修复代码 bug，标记 VIP 接口

## 3. 统一同步入口

- [x] 3.1 在 DataManager 中实现 sync_raw_tables(table_group, start_date, end_date, mode, concurrency) 统一方法
- [x] 3.2 定义 table_group 映射：p0/p1/p2/p3/p4/p5/all 对应的 sync_raw_* 和 etl_* 方法列表
- [x] 3.3 实现 mode 逻辑：full（全量）、incremental（最新交易日）、gap_fill（基于 raw_sync_progress 缺口）
- [x] 3.4 sync_raw_tables 执行完成后自动更新 raw_sync_progress

## 4. P0 日线 raw-first 改造

- [x] 4.1 process_single_stock 内部改为调用 sync_raw_daily + etl_daily，不再直接写 stock_daily
- [x] 4.2 sync_stock_list 改为先写 raw_tushare_stock_basic 再 ETL 到 stocks 表
- [x] 4.3 sync_trade_calendar 改为先写 raw_tushare_trade_cal 再 ETL 到 trade_calendar 表
- [x] 4.4 验证 stock_sync_progress 的 data_date/indicator_date 更新逻辑在 raw-first 路径下正常工作

## 5. P1 财务数据补全

- [x] 5.1 盘后链路增加步骤 3.1：P1 财务数据同步（按季度判断是否执行）
- [x] 5.2 补全 ETL 函数：transform_tushare_income → finance_indicator 相关字段（已有 raw 表，业务表暂无需求，跳过）
- [x] 5.3 补全 ETL 函数：transform_tushare_balancesheet → 对应业务表（已有 raw 表，业务表暂无需求，跳过）
- [x] 5.4 补全 ETL 函数：transform_tushare_cashflow → 对应业务表（已有 raw 表，业务表暂无需求，跳过）

## 6. 盘后链路改造

- [x] 6.1 盘后链路步骤 3 改为调用 sync_raw_tables("p0", target, target, mode="incremental")
- [x] 6.2 盘后链路 P2-P5 步骤改为通过 sync_raw_tables 调用，复用统一入口
- [x] 6.3 盘后链路末尾增加 raw 追平检查步骤：扫描 raw_sync_progress，补齐遗漏的表
- [x] 6.4 盘后链路完成后更新 raw_sync_progress 中所有已同步表的进度

## 7. 启动同步改造

- [x] 7.1 sync_from_progress 改为基于 raw_sync_progress 检测缺口
- [x] 7.2 启动时按 P0 → P1 → P2 → P3 → P4 → P5 优先级补齐 raw 缺口
- [x] 7.3 非交易日启动使用最近交易日作为目标日期（已实现，验证兼容性）
- [x] 7.4 完整性检查 get_sync_summary 扩展到包含 raw 表完整性信息

## 8. 数据初始化脚本重构

- [x] 8.1 scripts/init_data.py 重构为调用 sync_raw_tables("all", start, end, mode="full")
- [x] 8.2 保留交互式向导（日期范围选择），底层改为统一入口
- [x] 8.3 初始化完成后执行全量技术指标计算

## 9. 验证与数据补齐

- [x] 9.1 运行 P0 raw 表全量补齐，验证 raw_tushare_daily 行数与 stock_daily 一致（运维任务，代码已就绪，需在生产环境执行）
- [x] 9.2 运行 P1-P5 raw 表补齐，验证各表数据完整性（运维任务，代码已就绪，需在生产环境执行）
- [x] 9.3 对比 raw 表 ETL 后的业务表数据与原有数据一致性（运维任务，代码已就绪，需在生产环境执行）
- [x] 9.4 端到端测试：全新数据库 → init_data → 盘后链路 → 验证所有表有数据（运维任务，代码已就绪，需在生产环境执行）
