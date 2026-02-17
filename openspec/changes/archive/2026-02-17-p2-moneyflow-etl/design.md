## Context

V1 已完成 P2 资金流向 10 张 raw_tushare_* 表的建表（Alembic 迁移 `67b6a3dd7ed3`）、ORM 模型（`app/models/raw.py`）和 TushareClient fetch 方法（`app/data/tushare.py`）。业务表 `money_flow` 和 `dragon_tiger` 也已存在（`app/models/flow.py`）。

当前盘后链路（`run_post_market_chain`）流程为：交易日历 → 股票列表 → 进度初始化 → 批量数据拉取（日线+指标） → 缓存刷新 → 完整性门控 → 策略管道。资金流向同步需要插入到这个链路中。

P0 的 ETL 模式已经成熟：`sync_raw_daily` 按日期获取全市场数据写入 raw 表，`etl_daily` 从 raw 表 JOIN 清洗写入业务表。P2 ETL 遵循相同模式。

## Goals / Non-Goals

**Goals:**
- 实现 `raw_tushare_moneyflow` → `money_flow` 的 ETL 清洗
- 实现 `raw_tushare_top_list` + `raw_tushare_top_inst` → `dragon_tiger` 的 ETL 清洗
- 提供 DataManager 同步方法，支持按日期批量获取和清洗
- 集成到盘后链路，每日自动同步资金流向数据

**Non-Goals:**
- 不实现 moneyflow_dc/moneyflow_ths 等多源版本的 ETL（标准 moneyflow 接口已足够）
- 不实现市场级数据（moneyflow_hsgt/moneyflow_mkt_dc）的 ETL（无对应业务表，暂不需要）
- 不实现行业/概念级资金流向（moneyflow_ind_ths/moneyflow_cnt_ths/moneyflow_ind_dc）的 ETL
- 不修改业务表 schema（使用现有 money_flow 和 dragon_tiger 表结构）
- 不实现数据校验测试（由 Change 5 `data-validation-tests` 统一实施）

## Decisions

**D1: 只 ETL 核心 3 张 raw 表（moneyflow + top_list + top_inst），其余 7 张暂不处理**

10 张 raw 表中，`moneyflow` 是个股资金流向核心数据，`top_list` 和 `top_inst` 是龙虎榜数据。其余 7 张是不同数据源版本（东财/同花顺）或市场/行业级汇总数据，当前无对应业务表，暂不需要 ETL。

**D2: 资金流向同步插入盘后链路步骤 3 之后（批量数据拉取后、缓存刷新前）**

资金流向数据依赖交易日校验，但不影响技术指标计算和策略管道。作为独立步骤插入，失败不阻断后续链路。

**D3: 龙虎榜数据使用 UPSERT 而非 INSERT**

龙虎榜 `dragon_tiger` 表使用自增 id 主键，但同一股票同一天可能有多条记录（不同上榜原因）。使用 `(ts_code, trade_date, reason)` 作为唯一约束进行 UPSERT，避免重复插入。需要先添加唯一约束。

**D4: 复用现有 ETL 工具函数**

使用 `parse_date()`、`parse_decimal()`、`batch_insert()` 等已有工具函数，保持代码风格一致。

## Risks / Trade-offs

- [Tushare moneyflow 接口限流] → 使用已有 TokenBucket 限流，按日期获取全市场数据（单次 API 调用）
- [龙虎榜数据量不确定] → 每日龙虎榜股票数量有限（通常 20-50 只），数据量可控
- [dragon_tiger 表缺少唯一约束] → 需要添加 `(ts_code, trade_date, reason)` 唯一约束（Alembic 迁移）
