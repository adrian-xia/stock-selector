## 1. 策略管道数据补充

- [x] 1.1 修改 `app/strategy/pipeline.py` 的 `_enrich_finance_data()`，新增从 `raw_tushare_daily_basic` 查询估值指标（pe_ttm、pb、ps_ttm、dv_ttm→dividend_yield、total_mv、circ_mv），合并到 DataFrame
- [x] 1.2 验证现有 4 种基本面策略在数据补充后能正常工作（pe_ttm、dividend_yield 不再为 NULL）

## 2. 估值类策略实现

- [x] 2.1 实现 `app/strategy/fundamental/pb_value.py` — PB 低估值策略
- [x] 2.2 实现 `app/strategy/fundamental/peg_value.py` — PEG 估值策略
- [x] 2.3 实现 `app/strategy/fundamental/ps_value.py` — 市销率低估值策略

## 3. 盈利类策略实现

- [x] 3.1 实现 `app/strategy/fundamental/gross_margin_up.py` — 毛利率提升策略
- [x] 3.2 实现 `app/strategy/fundamental/cashflow_quality.py` — 现金流质量策略
- [x] 3.3 实现 `app/strategy/fundamental/profit_continuous_growth.py` — 净利润连续增长策略

## 4. 安全与综合策略实现

- [x] 4.1 实现 `app/strategy/fundamental/cashflow_coverage.py` — 经营现金流覆盖策略
- [x] 4.2 实现 `app/strategy/fundamental/quality_score.py` — 综合质量评分策略

## 5. 策略注册

- [x] 5.1 在 `app/strategy/factory.py` 中注册 8 种新基本面策略（总计 28 种：16 技术面 + 12 基本面）
- [x] 5.2 更新 `app/strategy/fundamental/__init__.py` 导出新策略类

## 6. 单元测试

- [x] 6.1 新增 `tests/unit/test_strategies_fundamental_new.py`，覆盖 8 种新策略的筛选逻辑（命中、不命中、数据缺失场景）
- [x] 6.2 新增策略工厂注册验证测试（总数 28、基本面 12）
- [x] 6.3 更新 `tests/unit/test_factory.py` 中的策略计数断言（20→28、4→12）

## 7. 文档同步

- [x] 7.1 更新 `docs/design/02-详细设计-策略引擎.md`，新增 §3.5 基本面策略扩展描述
- [x] 7.2 更新 `docs/design/99-实施范围-V1与V2划分.md`，标注基本面策略扩展为已实施
- [x] 7.3 更新 `README.md`，更新策略数量和基本面策略描述
- [x] 7.4 更新 `CLAUDE.md`，更新策略数量
- [x] 7.5 更新 `PROJECT_TASKS.md`，标注 Change 8 完成
