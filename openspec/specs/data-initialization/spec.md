## MODIFIED Requirements

### Requirement: 数据初始化使用 Tushare
数据初始化流程 SHALL 使用 TushareClient 替代 BaoStock/AKShare，支持从 DATA_START_DATE 配置的起始日期拉取全量历史数据。

#### Scenario: 初始化向导
- **WHEN** 运行 `uv run python -m scripts.init_data`
- **THEN** 使用 TushareClient 执行完整初始化流程（股票列表 → 交易日历 → 日线数据 → 技术指标）

#### Scenario: 支持更早的起始日期
- **WHEN** DATA_START_DATE 配置为 2006-01-01
- **THEN** 从 2006 年开始拉取全量历史数据
