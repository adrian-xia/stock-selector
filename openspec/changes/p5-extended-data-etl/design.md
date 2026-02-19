## Context

P5 核心已实施 20 张 raw 表的数据同步（sync_raw_*）和 2 个 ETL 清洗函数（suspend_d → suspend_info, limit_list_d → limit_list_daily）。TushareClient 已为全部 48 张 P5 raw 表实现了 fetch_raw_* 方法。剩余 28 张补充表的 raw 表已建表（Alembic 迁移），ORM 模型已定义，但尚未接入 DataManager 同步链路。

## Goals / Non-Goals

**Goals:**
- 为 28 张 P5 补充 raw 表新增 sync_raw_* 方法，接入数据同步链路
- 将新增方法按频率分组集成到 sync_p5_core 聚合入口
- 补充单元测试验证同步方法正确性

**Non-Goals:**
- 不新增业务表或 ETL 清洗函数（补充表直接查询 raw 表）
- 不修改盘后链路调度逻辑（sync_p5_core 已在步骤 3.8 中被调用）
- 不新增 API 端点或前端页面

## Decisions

### D1: 同步方法实现模式
复用现有 sync_raw_* 模式：调用 TushareClient.fetch_raw_* → _upsert_raw 写入 raw 表。每个方法独立，失败不影响其他表。

### D2: 频率分组策略
按数据更新频率分组集成到 sync_p5_core：
- **日频（9 张）**：hsgt_top10, limit_step, hm_detail, stk_auction, stk_auction_o, kpl_list, kpl_concept, broker_recommend, slb_len
- **静态/低频（12 张）**：namechange, stk_managers, stk_rewards, new_share, stk_list_his, stock_company（已有）, pledge_stat, pledge_detail, repurchase, share_float, report_rc, stk_surv
- **日频港股通（3 张）**：ggt_daily, ccass_hold, ccass_hold_detail, hk_hold
- **月频（1 张）**：ggt_monthly
- **日频因子（3 张）**：cyq_perf, cyq_chips（筹码数据随行情更新）

### D3: 静态数据同步频率
静态/低频数据（如 namechange, stk_managers 等）每季度首个交易日执行一次，与现有 stock_company、margin_target 保持一致。

### D4: 错误处理
每个 sync_raw_* 方法独立 try/except，单表失败记录 WARNING 日志但不阻断其他表同步，与现有 P5 核心模式一致。

## Risks / Trade-offs

- **API 限流风险**：新增 28 个接口调用会增加 Tushare API 负载，但令牌桶限流（400 QPS）可控制
- **同步耗时增加**：sync_p5_core 执行时间会增加，但均为非关键步骤，失败不阻断盘后链路
- **VIP 接口限制**：部分接口可能需要 Tushare VIP 权限，无权限时自动跳过并记录日志
