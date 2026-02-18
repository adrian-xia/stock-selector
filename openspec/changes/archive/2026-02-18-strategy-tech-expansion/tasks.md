## 1. 数据库与模型扩展

- [x] 1.1 在 `app/models/technical.py` 的 `TechnicalDaily` 模型新增 6 个字段：`wr`(Numeric(10,4))、`cci`(Numeric(10,4))、`bias`(Numeric(10,4))、`obv`(Numeric(20,2))、`donchian_upper`(Numeric(10,2))、`donchian_lower`(Numeric(10,2))
- [x] 1.2 创建 Alembic migration 为 `technical_daily` 表添加 6 个 nullable 列
- [x] 1.3 同步更新 `IndexTechnicalDaily` 和 `ConceptTechnicalDaily` 模型（如果它们共享相同的指标列结构）

## 2. 指标计算引擎扩展

- [x] 2.1 在 `app/data/indicator.py` 新增 `_compute_wr(high, low, close, period=14)` 函数
- [x] 2.2 在 `app/data/indicator.py` 新增 `_compute_cci(high, low, close, period=14)` 函数
- [x] 2.3 在 `app/data/indicator.py` 新增 `_compute_bias(close, ma20)` 函数
- [x] 2.4 在 `app/data/indicator.py` 新增 `_compute_obv(close, vol)` 函数
- [x] 2.5 在 `app/data/indicator.py` 新增 `_compute_donchian(high, low, period=20)` 函数
- [x] 2.6 更新 `compute_indicators_generic` 函数，调用上述 5 个新计算函数并写入结果列
- [x] 2.7 更新 `INDICATOR_COLUMNS` 列表，添加 `wr`、`cci`、`bias`、`obv`、`donchian_upper`、`donchian_lower`
- [x] 2.8 更新空 DataFrame 分支的 `indicator_cols` 列表

## 3. 趋势跟踪策略实现

- [x] 3.1 创建 `app/strategy/technical/donchian_breakout.py`，实现 `DonchianBreakoutStrategy`
- [x] 3.2 创建 `app/strategy/technical/atr_breakout.py`，实现 `ATRBreakoutStrategy`

## 4. 震荡指标策略实现

- [x] 4.1 创建 `app/strategy/technical/cci_oversold.py`，实现 `CCIOverboughtOversoldStrategy`
- [x] 4.2 创建 `app/strategy/technical/williams_r.py`，实现 `WilliamsRStrategy`
- [x] 4.3 创建 `app/strategy/technical/bias_oversold.py`，实现 `BIASStrategy`

## 5. 量价分析策略实现

- [x] 5.1 创建 `app/strategy/technical/volume_contraction.py`，实现 `VolumeContractionPullbackStrategy`
- [x] 5.2 创建 `app/strategy/technical/volume_price_divergence.py`，实现 `VolumePriceDivergenceStrategy`
- [x] 5.3 创建 `app/strategy/technical/obv_breakthrough.py`，实现 `OBVBreakthroughStrategy`

## 6. 策略注册

- [x] 6.1 在 `app/strategy/factory.py` 注册 8 个新策略的 `StrategyMeta`，确认 `get_all()` 返回 20 条、`get_by_category("technical")` 返回 16 条

## 7. 单元测试

- [x] 7.1 为 5 个新指标计算函数编写单元测试（`_compute_wr`、`_compute_cci`、`_compute_bias`、`_compute_obv`、`_compute_donchian`）
- [x] 7.2 为 `DonchianBreakoutStrategy` 和 `ATRBreakoutStrategy` 编写单元测试
- [x] 7.3 为 `CCIOverboughtOversoldStrategy`、`WilliamsRStrategy`、`BIASStrategy` 编写单元测试
- [x] 7.4 为 `VolumeContractionPullbackStrategy`、`VolumePriceDivergenceStrategy`、`OBVBreakthroughStrategy` 编写单元测试
- [x] 7.5 更新 `StrategyFactory` 测试，验证注册表包含 20 个策略

## 8. 文档同步

- [x] 8.1 更新 `docs/design/02-详细设计-策略引擎.md`，补充 8 种新策略说明
- [x] 8.2 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注技术面策略扩展为"✅ V1 已实施"
- [x] 8.3 更新 `README.md`（策略数量 12→20、技术指标数量 23→29、测试数量）
- [x] 8.4 更新 `CLAUDE.md`（V1 范围、数据库字段数、策略数量）
- [x] 8.5 更新 `PROJECT_TASKS.md`，标记 Change 7 完成
