## Why

V1 功能开发已全部完成（261 个测试用例，259 通过），但测试覆盖存在明显缺口：7 个 API 端点中有 5 个未测试，回测策略基类、数据源客户端等核心模块完全没有单元测试。同时 README.md 缺少 API 端点列表和测试数量统计。在进入系统测试和用户验收之前，需要补全这些缺口以确保代码质量。

## What Changes

### 测试补全（高优先级）
- 新增 `test_api_strategy.py` — 策略 API 3 个端点（run/list/schema）的单元测试
- 新增 `test_api_backtest_run.py` — 回测执行（POST /run）和结果查询（GET /result/{task_id}）端点测试
- 新增 `test_backtest_strategy.py` — AStockStrategy 基类和 SignalStrategy 的单元测试
- 新增 `test_backtest_data_feed.py` — 数据加载、前复权逻辑、DataFeed 构建测试

### 测试补全（中优先级）
- 新增 `test_baostock_client.py` — BaoStock 客户端：代码转换、重试、限流、数据解析
- 新增 `test_akshare_client.py` — AKShare 客户端：交易所推断、Decimal 转换、重试、数据解析

### 文档更新
- 更新 `README.md` — 补充 API 端点列表、测试数量统计

## Capabilities

### New Capabilities

- `api-test-coverage`: 覆盖策略 API 和回测 API 全部端点的单元测试
- `backtest-test-coverage`: 覆盖回测策略基类、数据加载的单元测试
- `data-client-test-coverage`: 覆盖 BaoStock 和 AKShare 客户端的单元测试

### Modified Capabilities

（无 spec 级别的需求变更，仅补充测试和文档）

## Impact

- **新增文件**: 6 个测试文件（`tests/unit/` 下）
- **修改文件**: `README.md`
- **预计新增测试用例**: 80-100 个
- **无代码逻辑变更**: 仅新增测试和更新文档，不修改任何业务代码
