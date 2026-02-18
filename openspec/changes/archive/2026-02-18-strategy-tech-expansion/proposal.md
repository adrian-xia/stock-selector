## Why

V1 实现了 8 种技术面策略，覆盖了均线、MACD、RSI、KDJ、布林带等基础指标。但实际选股中，趋势跟踪（唐奇安通道、ATR 突破）、震荡反转（CCI、Williams %R）和量价分析（缩量回调、量价背离）等维度缺失，导致策略覆盖面不足，容易遗漏有效信号。现有 `technical_daily` 表已包含 ATR、RSI 多周期等字段，数据基础已就绪，扩展策略的边际成本低。

## What Changes

- 新增 8 种技术面策略：
  - 趋势跟踪类：唐奇安通道突破、ATR 波动率突破
  - 震荡指标类：CCI 超买超卖、Williams %R 超卖反弹、BIAS 乖离率
  - 量价分析类：缩量回调、量价背离、OBV 能量潮突破
- 在 `strategy/factory.py` 注册新策略
- 新增 `wr` (Williams %R)、`cci`、`bias`、`obv` 四个技术指标字段到 `technical_daily` 表
- 更新指标计算器，新增上述四个指标的计算逻辑
- 更新前端策略列表展示（自动通过 API 获取，无需前端代码改动）

## Capabilities

### New Capabilities
- `trend-tracking-strategies`: 趋势跟踪类策略（唐奇安通道突破、ATR 波动率突破）
- `oscillator-strategies`: 震荡指标类策略（CCI 超买超卖、Williams %R 超卖反弹、BIAS 乖离率）
- `volume-price-strategies`: 量价分析类策略（缩量回调、量价背离、OBV 能量潮突破）
- `extended-technical-indicators`: 扩展技术指标计算（WR、CCI、BIAS、OBV）

### Modified Capabilities
- `strategy-factory`: 注册表新增 8 种技术面策略，`get_by_category("technical")` 返回 16 条
- `strategy-implementations`: 新增 8 种技术面策略的 filter_batch 实现
- `indicator-calculator`: 新增 WR、CCI、BIAS、OBV 四个指标的计算逻辑
- `database-schema`: `technical_daily` 表新增 `wr`、`cci`、`bias`、`obv` 四个字段

## Impact

- **代码变更**：`app/strategy/technical/` 新增 8 个策略文件，`app/strategy/factory.py` 新增注册项
- **数据库**：`technical_daily` 表新增 4 个字段（需 Alembic migration）
- **指标计算**：`app/data/indicator.py`（或等效模块）新增 4 个指标计算函数
- **测试**：每个新策略需配套单元测试
- **API**：无接口变更，新策略通过现有 `/api/v1/strategy/list` 自动暴露
- **依赖**：无新外部依赖，所有指标基于 Pandas/NumPy 计算
