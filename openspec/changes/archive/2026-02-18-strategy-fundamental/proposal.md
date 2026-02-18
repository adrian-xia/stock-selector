## Why

当前系统仅有 4 种基本面策略（低估值高成长、高股息、成长股、财务安全），覆盖面有限。设计文档 §3 规划了估值与价值、成长性、财务安全、机构动向四大类共 17 种基本面策略，当前实现率不足 25%。此外，现有策略存在数据缺失问题（`pe_ttm` 和 `dividend_yield` 字段为 NULL），导致部分策略无法正常工作。需要修复数据问题并扩展基本面策略库，提升选股系统的基本面分析能力。

## What Changes

- 修复 `finance_indicator` 表的 ETL 数据缺失：补充 `pe_ttm`（从 `raw_tushare_daily_basic`）和 `dividend_yield`（从 `raw_tushare_dividend` 计算）
- 新增 8 种基本面策略：
  - **PB 低估值策略**：市净率低于阈值，适合重资产行业价值投资
  - **PEG 估值策略**：PEG < 1 表示成长性被低估
  - **市销率低估值策略**：PS_TTM 低于阈值，适合高成长但尚未盈利的公司
  - **毛利率提升策略**：毛利率高于行业均值且呈上升趋势
  - **现金流充裕策略**：每股经营现金流 > 每股收益，现金流质量高
  - **净利润连续增长策略**：连续多期净利润正增长
  - **经营现金流覆盖策略**：经营现金流能覆盖短期负债
  - **综合质量评分策略**：多因子加权评分（ROE + 增长 + 安全 + 估值）
- 策略注册到 factory（总计 28 种：16 技术面 + 12 基本面）
- 新增单元测试覆盖所有新策略
- 同步更新文档（设计文档、README、CLAUDE.md）

## Capabilities

### New Capabilities
- `value-investing-strategies`: PB 低估值、PEG 估值、市销率低估值策略
- `profitability-strategies`: 毛利率提升、现金流充裕、净利润连续增长策略
- `safety-coverage-strategies`: 经营现金流覆盖策略
- `multi-factor-scoring`: 综合质量评分策略（多因子加权）

### Modified Capabilities
- `strategy-factory`: 注册新增 8 种基本面策略，总数从 20 增至 28
- `strategy-implementations`: 新增 8 种基本面策略实现
- `etl-pipeline`: 修复 finance_indicator 的 pe_ttm 和 dividend_yield ETL

## Impact

- **代码变更：** `app/strategy/fundamental/` 新增 8 个策略文件，`app/strategy/factory.py` 注册新策略，`app/data/etl.py` 修复 ETL
- **数据库：** 无新增表，仅修复 `finance_indicator` 现有字段的数据填充
- **API：** 无变更，新策略自动通过 `/api/v1/strategy/list` 暴露
- **测试：** 新增策略单元测试 + 工厂注册验证测试
- **依赖：** 无新增外部依赖
