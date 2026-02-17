## Context

P0-P5 数据采集体系已全部实施，包含 97 张 raw 表、26 张业务表和 18 个 ETL 清洗函数。当前仅有 `test_p0_data_validation.py`（7 个用例）和 `test_p1_data_validation.py`（5 个用例）两个集成测试文件，P2-P5 和综合校验完全缺失。

已有测试遵循统一模式：使用 `async_session_factory` 直连数据库，按 raw 完整性 → ETL 转换 → 数据质量 → 跨表一致性分层组织测试类。

## Goals / Non-Goals

**Goals:**
- 补全 P2-P5 数据校验测试，覆盖 raw 完整性、ETL 转换正确性、业务表数据质量
- 新增综合跨表一致性测试，验证时间连续性和跨优先级数据关联
- 所有测试遵循 P0/P1 已有模式，保持风格一致

**Non-Goals:**
- 不测试 raw 表中仅建表未同步的数据（P5 扩展的约 28 张补充表）
- 不做性能基准测试
- 不修改任何业务代码

## Decisions

### Decision 1: 按优先级分文件，综合校验独立文件
每个优先级一个测试文件（test_p2/p3/p4/p5），综合跨表校验单独一个文件（test_cross_table）。与 P0/P1 保持一致。

### Decision 2: 仅测试有 ETL 的业务表
P2 测试 money_flow + dragon_tiger，P3 测试 index_daily + index_weight + index_basic 等 6 张表，P4 测试 concept_index + concept_daily + concept_member，P5 测试 suspend_info + limit_list_daily。raw 表仅做记录数和关键字段非空检查。

### Decision 3: 复用已有测试模式
沿用 `async_session_factory` + `pytest.mark.asyncio` + `pytest.skip` 模式，不引入新的测试框架或 fixture。

### Decision 4: 阈值标准
- raw 表记录数：每个交易日 >= 上市股票数 × 0.90（资金流向覆盖率低于日线）
- 关键字段非空率：>= 90%
- raw → 业务表匹配度：>= 95%
- 时间连续性：最近 5 个交易日无缺失

## Risks / Trade-offs

- [测试依赖真实数据] → 使用 `pytest.skip` 处理无数据场景，CI 环境可标记跳过集成测试
- [阈值可能过严或过松] → 初始阈值参考 P0/P1 已有标准，后续根据实际数据调整
