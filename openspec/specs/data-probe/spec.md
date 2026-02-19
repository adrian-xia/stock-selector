## MODIFIED Requirements

### Requirement: 数据嗅探使用 Tushare
数据嗅探 SHALL 使用 TushareClient 检测数据是否就绪。

#### Scenario: 嗅探当日数据就绪
- **WHEN** 嗅探任务检测当日数据
- **THEN** 调用 Tushare daily 接口查询样本股票当日数据，判断数据是否已入库

#### Scenario: 嗅探阈值判断
- **WHEN** 80% 以上样本股票有当日数据
- **THEN** 判定数据已就绪，触发盘后链路
