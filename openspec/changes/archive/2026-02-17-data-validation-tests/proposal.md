## Why

P0-P5 数据采集体系已全部实施完成（97 张 raw 表 + 26 张业务表 + 18 个 ETL 函数），但数据校验测试仅覆盖 P0 和 P1（2 个测试文件），P2 资金流向、P3 指数、P4 板块、P5 扩展数据以及综合跨表一致性均无测试覆盖。需要补全校验测试确保数据质量可量化验证。

## What Changes

- 新增 `tests/integration/test_p2_data_validation.py`：P2 资金流向数据校验（moneyflow raw 完整性、ETL 转换、money_flow/dragon_tiger 业务表质量）
- 新增 `tests/integration/test_p3_data_validation.py`：P3 指数数据校验（index_daily/index_weight raw 完整性、ETL 转换、业务表质量）
- 新增 `tests/integration/test_p4_data_validation.py`：P4 板块数据校验（concept_index/concept_daily raw 完整性、ETL 转换、业务表质量）
- 新增 `tests/integration/test_p5_data_validation.py`：P5 扩展数据校验（suspend_d/limit_list_d raw 完整性、ETL 转换、suspend_info/limit_list_daily 业务表质量）
- 新增 `tests/integration/test_cross_table_validation.py`：综合跨表一致性校验（时间连续性、raw→业务表匹配度、跨优先级数据关联）

## Capabilities

### New Capabilities
- `data-validation`: 数据校验测试体系，覆盖 P2-P5 数据完整性、ETL 转换正确性、数据质量和跨表一致性

### Modified Capabilities
（无，本变更仅新增测试文件，不修改现有功能行为）

## Impact

- 新增 5 个集成测试文件，约 42 个测试用例
- 测试依赖真实数据库连接（集成测试，非 mock）
- 不影响现有代码和功能
