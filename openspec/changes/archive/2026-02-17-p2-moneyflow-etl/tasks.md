# P2 资金流向数据 ETL 实施任务

## 1. ETL 清洗函数

- [x] 1.1 在 `app/data/etl.py` 中实现 `transform_tushare_moneyflow(raw_rows)` 函数
  - 将 raw_tushare_moneyflow 原始数据转换为 money_flow 业务表格式
  - 日期 VARCHAR(8) → DATE，数值 NUMERIC → Decimal，NaN/None → 0
  - data_source 固定为 "tushare"
  - 跳过 ts_code 为空的记录

- [x] 1.2 在 `app/data/etl.py` 中实现 `transform_tushare_top_list(raw_rows)` 函数
  - 将 raw_tushare_top_list 原始数据转换为 dragon_tiger 业务表格式
  - 字段映射：l_buy → buy_total, l_sell → sell_total, net_amount → net_buy, reason → reason
  - data_source 固定为 "tushare"

- [x] 1.3 在 `app/data/etl.py` 中实现 `transform_tushare_top_inst(raw_rows)` 函数
  - 将 raw_tushare_top_inst 原始数据转换为标准格式（备用，暂不写入业务表）

## 2. DataManager 同步方法

- [x] 2.1 在 `app/data/manager.py` 中实现 `sync_raw_moneyflow(trade_date)` 方法
  - 调用 TushareClient.fetch_raw_moneyflow(td_str) 获取全市场个股资金流向
  - 使用 _upsert_raw 写入 raw_tushare_moneyflow 表
  - 返回 {"moneyflow": count}

- [x] 2.2 在 `app/data/manager.py` 中实现 `sync_raw_top_list(trade_date)` 方法
  - 并发调用 fetch_raw_top_list 和 fetch_raw_top_inst
  - 使用 _upsert_raw 分别写入 raw_tushare_top_list 和 raw_tushare_top_inst 表
  - 返回 {"top_list": count, "top_inst": count}

- [x] 2.3 在 `app/data/manager.py` 中实现 `etl_moneyflow(trade_date)` 方法
  - 从 raw_tushare_moneyflow 读取数据，调用 transform_tushare_moneyflow 清洗，写入 money_flow 业务表
  - 从 raw_tushare_top_list 读取数据，调用 transform_tushare_top_list 清洗，写入 dragon_tiger 业务表
  - 返回 {"money_flow": count, "dragon_tiger": count}

## 3. 数据库迁移

- [x] 3.1 为 dragon_tiger 表添加 `(ts_code, trade_date, reason)` 唯一约束（Alembic 迁移）
  - 支持 UPSERT 写入，避免重复数据

## 4. 盘后链路集成

- [x] 4.1 在 `app/scheduler/jobs.py` 的 `run_post_market_chain` 中增加资金流向同步步骤
  - 位置：步骤 3（批量数据拉取）之后、步骤 4（缓存刷新）之前
  - 调用 sync_raw_moneyflow + sync_raw_top_list + etl_moneyflow
  - 用 try/except 包裹，失败记录日志但不阻断后续链路

## 5. 导入和注册

- [x] 5.1 在 `app/data/manager.py` 中添加必要的 import（RawTushareMoneyflow, RawTushareTopList, RawTushareTopInst, MoneyFlow, DragonTiger, transform_tushare_moneyflow, transform_tushare_top_list）

## 6. 单元测试

- [x] 6.1 在 `tests/unit/test_etl.py` 中添加 transform_tushare_moneyflow 测试
  - 测试正常转换、空数据、缺失字段场景

- [x] 6.2 在 `tests/unit/test_etl.py` 中添加 transform_tushare_top_list 测试
  - 测试正常转换、空数据、字段映射场景

## 7. 文档更新

- [x] 7.1 更新 `docs/design/99-实施范围-V1与V2划分.md`，将 P2 资金流向标记为"✅ V1 已实施"（含 ETL 和数据同步）
- [x] 7.2 更新 `README.md` 和 `CLAUDE.md`，说明 P2 资金流向 ETL 已完成
