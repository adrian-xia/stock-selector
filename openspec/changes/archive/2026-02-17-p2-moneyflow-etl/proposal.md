## Why

V1 阶段已完成 P2 资金流向 10 张 raw 表的建表、ORM 模型和 TushareClient fetch 方法，但 ETL 清洗函数和 DataManager 数据同步方法尚未实施。资金流向数据是选股策略的重要维度（个股资金净流入/流出、龙虎榜机构动向），缺少 ETL 意味着 `money_flow` 和 `dragon_tiger` 业务表始终为空，资金流向相关策略无法运行。

## What Changes

- 新增 ETL 清洗函数：`transform_tushare_moneyflow`（个股资金流向）、`transform_tushare_top_list`（龙虎榜明细）、`transform_tushare_top_inst`（龙虎榜机构明细）
- 新增 DataManager 方法：`sync_raw_moneyflow(trade_date)` 同步原始数据、`etl_moneyflow(trade_date)` 清洗到业务表
- 盘后链路集成：在 `sync_raw_daily` 之后增加资金流向同步步骤
- 涉及 10 张 raw 表：moneyflow, moneyflow_dc, moneyflow_ths, moneyflow_hsgt, moneyflow_ind_ths, moneyflow_cnt_ths, moneyflow_ind_dc, moneyflow_mkt_dc, top_list, top_inst
- 目标业务表：`money_flow`（个股资金流向汇总）、`dragon_tiger`（龙虎榜数据）

## Capabilities

### New Capabilities
- `moneyflow-etl`: P2 资金流向数据的 ETL 清洗函数，将 raw_tushare_moneyflow* 原始数据转换为 money_flow/dragon_tiger 业务表格式
- `moneyflow-sync`: P2 资金流向数据的 DataManager 同步方法和盘后链路集成

### Modified Capabilities
- `etl-pipeline`: 新增 P2 资金流向 ETL 转换函数（transform_tushare_moneyflow 等）
- `data-manager`: 新增 sync_raw_moneyflow/etl_moneyflow 方法
- `scheduler-jobs`: 盘后链路增加资金流向同步步骤

## Impact

- **代码变更：** `app/data/etl.py`（新增 ETL 函数）、`app/data/manager.py`（新增同步方法）、`app/scheduler/jobs.py`（盘后链路集成）
- **数据库：** 无 schema 变更（raw 表和业务表均已存在），仅新增数据写入逻辑
- **API：** 无变更
- **依赖：** 无新增依赖，复用现有 TushareClient 和 ETL 工具函数
