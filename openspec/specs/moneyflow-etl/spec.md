## Requirements

### Requirement: 个股资金流向 ETL 清洗
系统 SHALL 提供 `transform_tushare_moneyflow(raw_rows)` 函数，将 `raw_tushare_moneyflow` 原始数据转换为 `money_flow` 业务表格式。

转换规则：
- `trade_date`: VARCHAR(8) YYYYMMDD → DATE
- `buy_sm_vol/amount`, `sell_sm_vol/amount` 等数值字段：NUMERIC → Decimal，NaN/None → 0
- `net_mf_amount`: 保留原始值
- `data_source`: 固定为 `"tushare"`
- 跳过 `ts_code` 为空的记录

#### Scenario: 正常转换
- **WHEN** 传入包含有效 moneyflow 原始数据的列表
- **THEN** 返回转换后的字典列表，日期为 DATE 类型，数值为 Decimal 类型，data_source 为 "tushare"

#### Scenario: 空数据
- **WHEN** 传入空列表
- **THEN** 返回空列表

#### Scenario: 缺失字段
- **WHEN** 原始数据中某些数值字段为 None 或 NaN
- **THEN** 对应字段转换为 0

### Requirement: 龙虎榜明细 ETL 清洗
系统 SHALL 提供 `transform_tushare_top_list(raw_rows)` 函数，将 `raw_tushare_top_list` 原始数据转换为 `dragon_tiger` 业务表格式。

字段映射：
- `l_buy` → `buy_total`
- `l_sell` → `sell_total`
- `net_amount` → `net_buy`
- `reason` → `reason`（直接透传）
- `data_source`: 固定为 `"tushare"`

#### Scenario: 正常转换
- **WHEN** 传入包含有效 top_list 原始数据的列表
- **THEN** 返回转换后的字典列表，字段映射正确

#### Scenario: 空数据
- **WHEN** 传入空列表
- **THEN** 返回空列表

### Requirement: 龙虎榜机构明细 ETL 清洗
系统 SHALL 提供 `transform_tushare_top_inst(raw_rows)` 函数，将 `raw_tushare_top_inst` 原始数据转换为可查询格式。该数据暂不写入业务表，仅提供 ETL 函数备用。

#### Scenario: 正常转换
- **WHEN** 传入包含有效 top_inst 原始数据的列表
- **THEN** 返回转换后的字典列表，日期为 DATE 类型，数值为 Decimal 类型
