## Why

数据采集和技术指标计算已完成，但系统还无法执行选股。策略引擎是核心业务模块——它定义选股策略、组织 5 层漏斗筛选管道、从 5000+ 只股票中筛选出候选池。回测引擎、AI 分析和前端都直接依赖策略引擎，必须先行实现。

## What Changes

- 新增 `BaseStrategy` 抽象基类，V1 采用扁平继承（所有策略直接继承 BaseStrategy，不设中间抽象子类）
- 新增 V1 核心策略实现（10-15 种），覆盖技术面和基本面两大类
- 新增 `StrategyFactory` 策略工厂，V1 使用手动字典注册（不用装饰器自动扫描）
- 新增 `Pipeline` 执行管道，实现 5 层漏斗筛选（SQL 粗筛 → 技术初筛 → 财务复筛 → 策略精筛 → AI 终审占位）
- V1 统一使用 `filter_batch` 单模式接口（去掉 `check_single` 双模式），所有策略接收 DataFrame 返回布尔 Series
- V1 策略组合仅支持 AND 逻辑（不支持嵌套 OR）
- 新增策略执行 HTTP API：`POST /api/v1/strategy/run`、`GET /api/v1/strategy/result/{task_id}`、`GET /api/v1/strategy/list`

## Capabilities

### New Capabilities
- `strategy-base`: BaseStrategy 抽象基类定义，包含 name/category/params 属性和 filter_batch 接口规范
- `strategy-implementations`: V1 核心策略实现（均线金叉、MACD 金叉、RSI 超卖、KDJ 金叉、布林带突破、放量突破、低估值高成长、高 ROE 成长、高股息等）
- `strategy-factory`: StrategyFactory 策略注册与实例化，手动字典映射，支持按分类/名称查询
- `strategy-pipeline`: Pipeline 5 层漏斗执行管道，Layer 1-4 实现 + Layer 5 AI 占位，策略组合 AND 逻辑
- `strategy-api`: 策略相关 HTTP API 路由（运行选股、查询结果、策略列表）

### Modified Capabilities
（无——策略引擎是全新模块，不修改现有 spec 的需求定义）

## Impact

- **新增目录：** `app/strategy/`（base.py、technical/、fundamental/、factory.py、pipeline.py）、`app/api/strategy.py`
- **依赖模块：** 消费 `data-manager` 的 `get_daily_bars()`、`get_latest_technical()`、`get_stock_list()` 接口
- **数据库：** 读取 `stocks`、`stock_daily`、`technical_daily`、`finance_indicator` 表；读写 `strategies` 表
- **HTTP API：** 新增 `/api/v1/strategy/` 路由组
- **后续模块依赖：** 回测引擎需要实例化策略并在历史数据上执行；前端需要调用策略 API
