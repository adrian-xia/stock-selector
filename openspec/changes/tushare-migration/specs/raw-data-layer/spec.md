## ADDED Requirements

### Requirement: 原始数据表与 Tushare API 输出一一对应
每个 Tushare 接口 SHALL 对应一张 `raw_tushare_*` 原始表，表字段与 API 输出字段一一对应，不做任何转换。日期字段保持 VARCHAR(8) 的 YYYYMMDD 格式，数值字段使用 NUMERIC。

#### Scenario: raw_tushare_daily 表结构
- **WHEN** 查看 `raw_tushare_daily` 表定义
- **THEN** 包含 ts_code/trade_date/open/high/low/close/pre_close/change/pct_chg/vol/amount 字段，主键为 (ts_code, trade_date)

#### Scenario: raw_tushare_adj_factor 表结构
- **WHEN** 查看 `raw_tushare_adj_factor` 表定义
- **THEN** 包含 ts_code/trade_date/adj_factor 字段，主键为 (ts_code, trade_date)

#### Scenario: raw_tushare_daily_basic 表结构
- **WHEN** 查看 `raw_tushare_daily_basic` 表定义
- **THEN** 包含 ts_code/trade_date/turnover_rate/pe/pe_ttm/pb/ps_ttm/total_mv/circ_mv 等字段，主键为 (ts_code, trade_date)

### Requirement: 原始表包含 fetched_at 时间戳
每张 raw 表 SHALL 包含 `fetched_at` 字段（TIMESTAMP DEFAULT NOW()），记录数据拉取时间。

#### Scenario: 数据写入时自动记录时间
- **WHEN** 向 raw 表插入数据
- **THEN** `fetched_at` 字段自动填充当前时间戳

### Requirement: 原始表使用 ON CONFLICT DO UPDATE
原始表写入 SHALL 使用 `INSERT ... ON CONFLICT DO UPDATE`，确保重复拉取时更新数据而非报错。

#### Scenario: 重复拉取同一天数据
- **WHEN** 对同一个 (ts_code, trade_date) 重复写入
- **THEN** 更新已有记录的数据字段和 fetched_at 时间戳

### Requirement: P0 核心原始表（6 张）
系统 SHALL 包含以下 P0 核心原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 1 | raw_tushare_stock_basic | stock_basic | 股票列表 |
| 2 | raw_tushare_trade_cal | trade_cal | 交易日历 |
| 3 | raw_tushare_daily | daily | A股日线行情 |
| 4 | raw_tushare_adj_factor | adj_factor | 复权因子 |
| 5 | raw_tushare_daily_basic | daily_basic | 每日指标 |
| 6 | raw_tushare_stk_limit | stk_limit | 涨跌停价格 |

#### Scenario: P0 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 6 张 P0 原始表

### Requirement: P1 财务原始表（10 张）
系统 SHALL 包含以下 P1 财务原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 7 | raw_tushare_fina_indicator | fina_indicator / fina_indicator_vip | 财务指标（VIP 版共用同一张 raw 表） |
| 8 | raw_tushare_income | income / income_vip | 利润表 |
| 9 | raw_tushare_balancesheet | balancesheet / balancesheet_vip | 资产负债表 |
| 10 | raw_tushare_cashflow | cashflow / cashflow_vip | 现金流量表 |
| 11 | raw_tushare_dividend | dividend | 分红送股 |
| 12 | raw_tushare_forecast | forecast / forecast_vip | 业绩预告 |
| 13 | raw_tushare_express | express / express_vip | 业绩快报 |
| 14 | raw_tushare_fina_audit | fina_audit | 财务审计意见 |
| 15 | raw_tushare_fina_mainbz | fina_mainbz / fina_mainbz_vip | 主营业务构成 |
| 16 | raw_tushare_disclosure_date | disclosure_date | 财报披露计划 |

#### Scenario: P1 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 10 张 P1 原始表

### Requirement: P2 资金流向原始表（8 张）
系统 SHALL 包含以下 P2 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 17 | raw_tushare_moneyflow | moneyflow | 个股资金流向 |
| 18 | raw_tushare_moneyflow_dc | moneyflow_dc | 个股资金流向(DC) |
| 19 | raw_tushare_moneyflow_ths | moneyflow_ths | 个股资金流向(THS) |
| 20 | raw_tushare_moneyflow_hsgt | moneyflow_hsgt | 沪深港通资金流向 |
| 21 | raw_tushare_moneyflow_ind_ths | moneyflow_ind_ths | 同花顺行业资金流向 |
| 22 | raw_tushare_moneyflow_cnt_ths | moneyflow_cnt_ths | 同花顺概念板块资金流向 |
| 23 | raw_tushare_moneyflow_ind_dc | moneyflow_ind_dc | 东财板块资金流向 |
| 24 | raw_tushare_moneyflow_mkt_dc | moneyflow_mkt_dc | 大盘资金流向(DC) |

#### Scenario: P2 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 8 张 P2 原始表

### Requirement: P3 基础数据补充原始表（7 张）
系统 SHALL 包含以下 P3 基础数据补充原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 25 | raw_tushare_namechange | namechange | 股票曾用名 |
| 26 | raw_tushare_stock_company | stock_company | 上市公司基本信息 |
| 27 | raw_tushare_stk_managers | stk_managers | 上市公司管理层 |
| 28 | raw_tushare_stk_rewards | stk_rewards | 管理层薪酬和持股 |
| 29 | raw_tushare_new_share | new_share | IPO新股列表 |
| 30 | raw_tushare_daily_share | daily_share | 股本情况（盘前） |
| 31 | raw_tushare_stk_list_his | stk_list_his | 股票历史列表 |

#### Scenario: P3 基础补充表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 7 张 P3 基础补充原始表

### Requirement: P4 行情补充原始表（5 张）
系统 SHALL 包含以下 P4 行情补充原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 32 | raw_tushare_weekly | weekly | 周线行情 |
| 33 | raw_tushare_monthly | monthly | 月线行情 |
| 34 | raw_tushare_suspend_d | suspend_d | 停复牌信息 |
| 35 | raw_tushare_hsgt_top10 | hsgt_top10 | 沪深股通十大成交股 |
| 36 | raw_tushare_ggt_daily | ggt_daily | 港股通每日成交统计 |

#### Scenario: P4 行情补充表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 5 张 P4 行情补充原始表

### Requirement: P5 市场参考数据原始表（9 张）
系统 SHALL 包含以下 P5 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 37 | raw_tushare_top10_holders | top10_holders | 前十大股东 |
| 38 | raw_tushare_top10_floatholders | top10_floatholders | 前十大流通股东 |
| 39 | raw_tushare_pledge_stat | pledge_stat | 股权质押统计 |
| 40 | raw_tushare_pledge_detail | pledge_detail | 股权质押明细 |
| 41 | raw_tushare_repurchase | repurchase | 股票回购 |
| 42 | raw_tushare_share_float | share_float | 限售股解禁 |
| 43 | raw_tushare_block_trade | block_trade | 大宗交易 |
| 44 | raw_tushare_stk_holdernumber | stk_holdernumber | 股东人数 |
| 45 | raw_tushare_stk_holdertrade | stk_holdertrade | 股东增减持 |

#### Scenario: P5 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 9 张 P5 原始表

### Requirement: P6 特色数据原始表（9 张）
系统 SHALL 包含以下 P6 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 46 | raw_tushare_report_rc | report_rc | 券商盈利预测 |
| 47 | raw_tushare_cyq_perf | cyq_perf | 筹码分布绩效 |
| 48 | raw_tushare_cyq_chips | cyq_chips | 筹码分布明细 |
| 49 | raw_tushare_stk_factor | stk_factor | 股票技术面因子 |
| 50 | raw_tushare_stk_factor_pro | stk_factor_pro | 技术面因子(专业版) |
| 51 | raw_tushare_ccass_hold | ccass_hold | 中央结算系统持股统计 |
| 52 | raw_tushare_ccass_hold_detail | ccass_hold_detail | 中央结算系统持股明细 |
| 53 | raw_tushare_hk_hold | hk_hold | 沪深港股通持股明细 |
| 54 | raw_tushare_stk_surv | stk_surv | 机构调研 |

#### Scenario: P6 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 9 张 P6 原始表

### Requirement: P7 两融原始表（4 张）
系统 SHALL 包含以下 P7 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 55 | raw_tushare_margin | margin | 融资融券交易汇总 |
| 56 | raw_tushare_margin_detail | margin_detail | 融资融券交易明细 |
| 57 | raw_tushare_margin_target | margin_target | 融资融券标的 |
| 58 | raw_tushare_slb_len | slb_len | 转融资交易汇总 |

#### Scenario: P7 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 4 张 P7 原始表

### Requirement: P8 打板专题原始表（14 张）
系统 SHALL 包含以下 P8 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 59 | raw_tushare_top_list | top_list | 龙虎榜每日明细 |
| 60 | raw_tushare_top_inst | top_inst | 龙虎榜机构明细 |
| 61 | raw_tushare_limit_list_d | limit_list_d | 涨跌停列表(新) |
| 62 | raw_tushare_ths_limit | ths_limit | 涨跌停榜单(同花顺) |
| 63 | raw_tushare_limit_step | limit_step | 连板天梯 |
| 64 | raw_tushare_hm_board | hm_board | 最强板块统计 |
| 65 | raw_tushare_hm_list | hm_list | 游资名录 |
| 66 | raw_tushare_hm_detail | hm_detail | 游资每日明细 |
| 67 | raw_tushare_stk_auction | stk_auction | 集合竞价数据 |
| 68 | raw_tushare_stk_auction_o | stk_auction_o | 当日开盘集合竞价 |
| 69 | raw_tushare_kpl_list | kpl_list | 开盘啦榜单数据 |
| 70 | raw_tushare_kpl_concept | kpl_concept | 开盘啦题材库 |
| 71 | raw_tushare_broker_recommend | broker_recommend | 券商月度金股 |
| 72 | raw_tushare_ths_hot | ths_hot | 同花顺热榜 |

#### Scenario: P8 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 14 张 P8 原始表

### Requirement: P9 板块原始表（8 张）
系统 SHALL 包含以下 P9 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 73 | raw_tushare_ths_index | ths_index | 同花顺概念和行业指数 |
| 74 | raw_tushare_ths_daily | ths_daily | 同花顺板块指数行情 |
| 75 | raw_tushare_ths_member | ths_member | 同花顺概念板块成分 |
| 76 | raw_tushare_dc_index | dc_index | 东方财富概念板块 |
| 77 | raw_tushare_dc_member | dc_member | 东方财富板块成分 |
| 78 | raw_tushare_dc_hot_new | dc_hot_new | 东方财富热板 |
| 79 | raw_tushare_tdx_index | tdx_index | 通达信板块信息 |
| 80 | raw_tushare_tdx_member | tdx_member | 通达信板块成分 |

#### Scenario: P9 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 8 张 P9 原始表

### Requirement: P10 指数原始表（12 张）
系统 SHALL 包含以下 P10 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 81 | raw_tushare_index_basic | index_basic | 指数基本信息 |
| 82 | raw_tushare_index_weight | index_weight | 指数成分和权重 |
| 83 | raw_tushare_index_daily | index_daily | 指数日线行情 |
| 84 | raw_tushare_index_weekly | index_weekly | 指数周线行情 |
| 85 | raw_tushare_index_monthly | index_monthly | 指数月线行情 |
| 86 | raw_tushare_index_dailybasic | index_dailybasic | 大盘指数每日指标 |
| 87 | raw_tushare_index_global | index_global | 国际主要指数 |
| 88 | raw_tushare_daily_info | daily_info | 沪深市场每日交易统计 |
| 89 | raw_tushare_sz_daily_info | sz_daily_info | 深圳市场每日交易情况 |
| 90 | raw_tushare_index_classify | index_classify | 申万行业分类 |
| 91 | raw_tushare_index_member_all | index_member_all | 申万行业成分 |
| 92 | raw_tushare_sw_daily | sw_daily | 申万行业指数日行情 |

#### Scenario: P10 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 12 张 P10 原始表

### Requirement: P11 中信行业 + 指数技术面原始表（4 张）
系统 SHALL 包含以下 P11 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 93 | raw_tushare_ci_index_member | ci_index_member | 中信行业成分 |
| 94 | raw_tushare_ci_daily | ci_daily | 中信行业指数日行情 |
| 95 | raw_tushare_index_factor_pro | index_factor_pro | 指数技术面因子(专业版) |
| 96 | raw_tushare_tdx_daily | tdx_daily | 通达信板块行情 |

#### Scenario: P11 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 4 张 P11 原始表

### Requirement: P12 港股通补充原始表（2 张）
系统 SHALL 包含以下 P12 原始表：

| # | raw 表名 | 对应 API | 说明 |
|---|---------|---------|------|
| 97 | raw_tushare_ggt_monthly | ggt_monthly | 港股通每月成交统计 |
| 98 | raw_tushare_dc_hot | dc_hot | 东财概念板块行情 |

#### Scenario: P12 表全部存在
- **WHEN** 执行 alembic upgrade head
- **THEN** 数据库中存在上述 2 张 P12 原始表

### Requirement: 排除项说明
以下接口不创建 raw 表：
- `pro_bar`（通用行情接口）— 与 daily/weekly/monthly 功能重复，通过它们获取数据
- `realtime_rank` / `realtime_tick` / `realtime_list`（3 个爬虫版）— 实时数据不落库
- `sw_realtime`（申万实时行情）— 实时数据不落库
- `anns_d`（全量公告）— 需要独立权限，当前不可用
- VIP 版本（income_vip 等 6 个）— 与标准版共用同一张 raw 表，VIP 只是获取方式不同

#### Scenario: 排除接口不建表
- **WHEN** 执行 alembic upgrade head
- **THEN** 不存在 raw_tushare_pro_bar / raw_tushare_realtime_* / raw_tushare_sw_realtime / raw_tushare_anns_d 表

### Requirement: raw 表总数
系统 SHALL 共包含 98 张 raw_tushare_* 原始表，覆盖 6000 积分可用的全部非实时、非重复接口。

#### Scenario: 验证 raw 表总数
- **WHEN** 查询数据库中以 raw_tushare_ 开头的表
- **THEN** 共计 98 张表
