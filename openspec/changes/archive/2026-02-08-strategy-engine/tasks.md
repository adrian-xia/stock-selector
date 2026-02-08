## 1. 模块骨架与基类

- [x] 1.1 创建 `app/strategy/` 目录结构：`__init__.py`、`base.py`、`factory.py`、`pipeline.py`、`technical/__init__.py`、`fundamental/__init__.py`
- [x] 1.2 实现 `BaseStrategy` 抽象基类（`base.py`）：定义 name/display_name/category/description/default_params 属性，`__init__` 合并 params，抽象方法 `filter_batch(df, target_date) -> Series[bool]`
- [x] 1.3 实现 `StrategyMeta` 数据类和 `StrategyFactory`（`factory.py`）：`STRATEGY_REGISTRY` 字典、`get_strategy()`、`get_all()`、`get_by_category()`、`get_meta()` 方法

## 2. 技术面策略实现

- [x] 2.1 实现 `MACrossStrategy`（均线金叉）：MA5 上穿 MA10 + 放量确认，使用 `_prev` 列做交叉检测
- [x] 2.2 实现 `MACDGoldenStrategy`（MACD 金叉）：DIF 上穿 DEA
- [x] 2.3 实现 `RSIOversoldStrategy`（RSI 超卖反弹）：RSI6 从超卖区回升
- [x] 2.4 实现 `KDJGoldenStrategy`（KDJ 金叉）：K 上穿 D 且 J 在低位
- [x] 2.5 实现 `BollBreakthroughStrategy`（布林带突破）：价格从下轨下方回升
- [x] 2.6 实现 `VolumeBreakoutStrategy`（放量突破）：创 20 日新高 + 量比 > 2
- [x] 2.7 实现 `MALongArrangeStrategy`（均线多头排列）：MA5 > MA10 > MA20 > MA60
- [x] 2.8 实现 `MACDDivergenceStrategy`（MACD 底背离）：价格新低但 DIF 不创新低

## 3. 基本面策略实现

- [x] 3.1 实现 `LowPEHighROEStrategy`（低估值高成长）：PE < 30, ROE > 15%, 利润增长 > 20%
- [x] 3.2 实现 `HighDividendStrategy`（高股息）：股息率 > 3%, PE < 20
- [x] 3.3 实现 `GrowthStockStrategy`（成长股）：营收增长 > 20%, 利润增长 > 20%
- [x] 3.4 实现 `FinancialSafetyStrategy`（财务安全）：资产负债率 < 60%, 流动比率 > 1.5

## 4. 策略注册

- [x] 4.1 在 `factory.py` 中注册全部 12 种策略到 `STRATEGY_REGISTRY`，填写完整的 StrategyMeta 元数据

## 5. Pipeline 执行管道

- [x] 5.1 实现 `PipelineResult` 和 `StockPick` 数据类（`pipeline.py`）
- [x] 5.2 实现 Layer 1：SQL 查询获取当日可交易股票列表（剔除 ST/停牌/退市/低流动性）
- [x] 5.3 实现市场快照 DataFrame 构建：JOIN stock_daily + technical_daily + 前日 technical_daily（_prev 列）+ finance_indicator（最新报告期）
- [x] 5.4 实现 Layer 2-3：遍历选中策略执行 filter_batch，按 category 分层，记录每只股票命中的策略列表
- [x] 5.5 实现 Layer 4：按命中策略数降序排序，取 Top N
- [x] 5.6 实现 Layer 5 AI 占位：直接透传 Layer 4 结果
- [x] 5.7 实现 `execute_pipeline()` 主函数：串联 Layer 1-5，计时，返回 PipelineResult

## 6. HTTP API

- [x] 6.1 创建 `app/api/strategy.py`：实现 `POST /api/v1/strategy/run` 端点（Pydantic 请求/响应模型 + 调用 execute_pipeline）
- [x] 6.2 实现 `GET /api/v1/strategy/list` 端点：返回策略列表，支持 category 过滤
- [x] 6.3 实现 `GET /api/v1/strategy/schema/{name}` 端点：返回策略参数元数据
- [x] 6.4 在 `app/main.py` 中注册策略 API 路由

## 7. 单元测试

- [x] 7.1 编写 `tests/unit/test_strategy_base.py`：测试 BaseStrategy 实例化、params 合并
- [x] 7.2 编写 `tests/unit/test_strategies.py`：测试每种策略的 filter_batch 逻辑（构造 DataFrame 验证布尔输出）
- [x] 7.3 编写 `tests/unit/test_factory.py`：测试 StrategyFactory 注册、查询、实例化
- [x] 7.4 编写 `tests/unit/test_pipeline.py`：测试 Pipeline 各层逻辑（使用 mock DataManager）
