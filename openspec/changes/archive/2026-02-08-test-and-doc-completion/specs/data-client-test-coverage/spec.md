## ADDED Requirements

### Requirement: BaoStock 客户端测试覆盖
系统 SHALL 为 BaoStock 客户端提供单元测试，覆盖代码转换、数据解析和重试逻辑。

#### Scenario: 标准代码转 BaoStock 格式
- **WHEN** 输入 "600519.SH"
- **THEN** 转换为 "sh.600519"

#### Scenario: BaoStock 格式转标准代码
- **WHEN** 输入 "sh.600519"
- **THEN** 转换为 "600519.SH"

#### Scenario: 深圳代码转换
- **WHEN** 输入 "000001.SZ"
- **THEN** 转换为 "sz.000001"

#### Scenario: 日线数据解析
- **WHEN** BaoStock 返回原始日线数据行
- **THEN** 解析为标准字典格式，包含 ts_code、trade_date、open、high、low、close、vol 等字段

#### Scenario: 重试机制生效
- **WHEN** 首次请求失败，第二次成功
- **THEN** 自动重试并返回成功结果

#### Scenario: 健康检查
- **WHEN** 调用 health_check
- **THEN** 返回布尔值表示 BaoStock 服务是否可用

### Requirement: AKShare 客户端测试覆盖
系统 SHALL 为 AKShare 客户端提供单元测试，覆盖交易所推断、数据转换和重试逻辑。

#### Scenario: 交易所推断 - 上海
- **WHEN** 输入以 6 开头的股票代码（如 "600519.SH"）
- **THEN** 推断交易所为 "SH"

#### Scenario: 交易所推断 - 深圳
- **WHEN** 输入以 0 或 3 开头的股票代码（如 "000001.SZ"）
- **THEN** 推断交易所为 "SZ"

#### Scenario: Decimal 转换处理 NaN
- **WHEN** 输入值为 NaN 或空字符串
- **THEN** 返回 None 而非抛出异常

#### Scenario: 日线数据解析
- **WHEN** AKShare 返回原始 DataFrame
- **THEN** 解析为标准字典列表，字段名和类型符合规范

#### Scenario: 重试机制生效
- **WHEN** 首次请求抛出异常，第二次成功
- **THEN** 自动重试并返回成功结果

#### Scenario: 股票列表获取
- **WHEN** 调用 fetch_stock_list
- **THEN** 返回包含 ts_code、name、list_date 等字段的字典列表
