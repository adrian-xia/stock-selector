## Context

V1 全部功能已实现，当前有 261 个测试用例（259 通过，2 个集成测试因需要真实数据库而跳过）。项目使用 pytest + asyncio_mode="auto"，API 测试通过 `unittest.mock.patch` mock 数据库会话，直接调用端点函数（不使用 httpx/TestClient）。

现有测试覆盖了策略引擎、回测引擎核心、AI 模块、缓存层、调度器等模块，但以下模块缺失测试：
- API 层：7 个端点中仅 2 个有测试（backtest/list、data/kline）
- 回测策略基类（AStockStrategy、SignalStrategy）
- 回测数据加载（data_feed.py）
- 数据源客户端（baostock.py、akshare.py）

## Goals / Non-Goals

**Goals:**
- 补全 API 层全部端点的单元测试
- 补全回测策略基类和数据加载模块的单元测试
- 补全数据源客户端的单元测试（代码转换、重试、数据解析）
- 更新 README.md 补充 API 端点列表和测试数量
- 所有新增测试遵循现有测试模式（mock 数据库、直接调用函数）

**Non-Goals:**
- 不修改任何业务代码
- 不追求 100% 行覆盖率，聚焦核心逻辑路径
- 不新增集成测试或端到端测试
- 不引入新的测试依赖（httpx 等）

## Decisions

### 1. API 测试模式：直接调用函数 + mock session

沿用现有模式（`test_api_backtest_list.py`、`test_api_data.py`），通过 `@patch("app.api.xxx.async_session_factory")` mock 数据库，直接调用端点函数验证返回值。

**理由**: 与现有测试保持一致，无需引入 TestClient，测试更轻量。

### 2. Backtrader 策略测试：使用真实 Cerebro 运行

AStockStrategy 和 SignalStrategy 需要在 Backtrader 引擎中运行才能测试。构造内存中的 DataFrame 作为 DataFeed，用小数据集（10-20 条 bar）验证买卖逻辑。

**理由**: Backtrader 策略依赖引擎的事件循环，无法脱离 Cerebro 单独测试。现有 `test_backtest_engine.py` 已有此模式。

### 3. 数据源客户端测试：mock 外部 API

BaoStock 和 AKShare 客户端测试通过 mock 底层库调用（`baostock.query_history_k_data_plus`、`akshare.stock_zh_a_hist`），验证代码转换、数据解析、重试逻辑。

**理由**: 不依赖外部服务，测试可离线运行且稳定。

### 4. 数据加载测试：mock AsyncSession

`load_stock_data()` 测试通过 mock AsyncSession 返回预设数据，验证前复权公式和 DataFrame 结构。`build_data_feed()` 直接用内存 DataFrame 验证字段映射。

### 5. 文档更新范围

README.md 新增 "API 端点" 章节，列出全部 7 个端点的方法、路径和说明。更新测试数量为补全后的实际数字。

## Risks / Trade-offs

- **Backtrader 策略测试较慢** → 使用最小数据集（10-20 条 bar），控制单个测试在 100ms 内
- **mock 过多可能掩盖真实问题** → 聚焦验证业务逻辑（参数校验、数据转换、错误处理），不测试框架行为
- **数据源 API 变更导致 mock 失效** → 这是单元测试的固有局限，集成测试（V2）再覆盖
