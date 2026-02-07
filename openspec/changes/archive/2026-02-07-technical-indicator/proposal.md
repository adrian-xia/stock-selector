## Why

策略引擎的技术面策略（均线金叉、MACD 金叉、RSI 超卖、布林带突破等）全部依赖预计算的技术指标。当前 `technical_daily` 表已建好但没有计算逻辑填充数据，策略引擎无法工作。技术指标计算是数据采集到策略引擎之间的关键桥梁，必须在策略引擎之前实现。

## What Changes

- 新增技术指标计算引擎（`app/data/indicator.py`），基于 pandas 向量化计算所有指标
- 新增单只股票指标计算函数：输入日线 DataFrame，输出含全部指标列的 DataFrame
- 新增全市场批量计算逻辑：遍历所有股票，计算并写入 `technical_daily` 表
- 新增增量计算逻辑：仅计算最新交易日的指标（每日收盘后调用）
- 新增 CLI 命令：`compute-indicators`（全量）和 `update-indicators`（增量）
- 在 DataManager 中新增 `get_latest_technical()` 查询接口，供策略引擎使用

## Capabilities

### New Capabilities
- `indicator-calculator`: 技术指标计算引擎，包含 MA/MACD/KDJ/RSI/BOLL/ATR/量比等全部指标的向量化计算函数，支持单股票计算和全市场批量计算，以及增量更新
- `indicator-cli`: CLI 命令用于全量计算和增量更新技术指标

### Modified Capabilities
- `data-manager`: 新增 `get_latest_technical()` 查询接口，从 `technical_daily` 表读取最新技术指标

## Impact

- **新增依赖：** 无（pandas 已在依赖中）
- **依赖模块：** 依赖 `data-manager` 提供的 `stock_daily` 数据和 `DataManager`
- **数据库：** 写入已有的 `technical_daily` 表，不新增表
- **后续模块依赖：** 策略引擎的技术面策略直接消费 `technical_daily` 数据
