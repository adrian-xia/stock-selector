## Context

当前系统有 4 种基本面策略（低估值高成长、高股息、成长股、财务安全），但存在两个关键数据问题：

1. **ETL 数据缺失：** `transform_tushare_fina_indicator()` 中 `pe_ttm`、`pb`、`ps_ttm`、`total_mv`、`circ_mv` 被硬编码为 `None`，注释说明应从 `raw_tushare_daily_basic` 获取但未实现
2. **字段缺失：** `FinanceIndicator` 模型中没有 `dividend_yield` 字段，高股息策略实际无法工作

数据源已就绪：`raw_tushare_daily_basic` 表包含 `pe_ttm`、`dv_ttm`（股息率TTM）、`total_mv`、`circ_mv` 等字段。

## Goals / Non-Goals

**Goals:**
- 修复 `finance_indicator` 表的估值指标数据填充（pe_ttm、pb、ps_ttm、total_mv、circ_mv）
- 新增 `dividend_yield` 字段并从 `raw_tushare_daily_basic.dv_ttm` 填充
- 新增 8 种基本面策略，总计 12 种基本面策略
- 更新策略管道的财务数据补充逻辑
- 完整的单元测试覆盖

**Non-Goals:**
- 机构动向策略（北向资金、机构调研）— 数据源复杂度高，留待后续
- 行业轮动策略 — 需要行业分类数据的深度整合，留待后续
- 多因子动态权重优化 — 属于参数优化模块（Change 9）
- 因子有效性回测 — 属于参数优化模块（Change 9）

## Decisions

### D1: 估值指标数据来源 — 从 daily_basic 补充而非 fina_indicator ETL 内计算

**选择：** 在策略管道的 `_enrich_finance_data()` 中直接从 `raw_tushare_daily_basic` 查询估值指标，而非在 `transform_tushare_fina_indicator()` ETL 中补充。

**理由：**
- `finance_indicator` 按报告期（季度）存储，而 `daily_basic` 的估值指标是每日变化的
- 策略执行时需要的是目标交易日当天的 PE/PB/股息率，不是报告期的
- 直接在管道中查询 daily_basic 更准确，避免数据时效性问题
- 保持 ETL 函数的单一职责（只处理财务报表数据）

**替代方案：** 在 ETL 中用报告期末的 daily_basic 数据填充 → 数据不够实时，PE 等指标每天变化

### D2: dividend_yield 处理 — 使用 daily_basic.dv_ttm 而非从 dividend 表计算

**选择：** 直接使用 `raw_tushare_daily_basic.dv_ttm`（Tushare 预计算的 TTM 股息率）。

**理由：**
- Tushare 已经计算好了 TTM 股息率，无需自行从分红记录计算
- 避免复杂的分红计算逻辑（需要考虑除权日、税率等）
- 数据每日更新，时效性好

### D3: 策略管道数据补充 — 扩展 _enrich_finance_data 增加 daily_basic 查询

**选择：** 在现有 `_enrich_finance_data()` 函数中增加一个 `raw_tushare_daily_basic` 查询，补充估值指标。

**实现方式：**
```
_enrich_finance_data():
  1. 查询 finance_indicator（现有逻辑，获取 ROE/增长率/负债率等）
  2. 新增：查询 raw_tushare_daily_basic（获取 pe_ttm/pb/ps_ttm/dv_ttm/total_mv/circ_mv）
  3. 合并两个数据源到 DataFrame
```

### D4: 新策略设计 — 8 种策略全部使用 filter_batch 模式

**选择：** 所有新策略继承 `BaseStrategy`，实现 `filter_batch()` 方法，返回布尔 Series。

**8 种新策略：**

| 策略名 | 文件名 | 筛选逻辑 | 数据依赖 |
|--------|--------|----------|----------|
| pb-value | pb_value.py | PB < 阈值 AND PB > 0 | pb (daily_basic) |
| peg-value | peg_value.py | PEG < 1（PE_TTM / profit_yoy） | pe_ttm, profit_yoy |
| ps-value | ps_value.py | PS_TTM < 阈值 AND PS_TTM > 0 | ps_ttm (daily_basic) |
| gross-margin-up | gross_margin_up.py | 毛利率 > 阈值 | gross_margin |
| cashflow-quality | cashflow_quality.py | 每股经营现金流 > 每股收益 | ocf_per_share, eps |
| profit-continuous-growth | profit_continuous_growth.py | 利润同比增长 > 0 连续 N 期 | profit_yoy |
| cashflow-coverage | cashflow_coverage.py | 经营现金流 / 流动负债 > 阈值 | ocf_per_share, current_ratio |
| quality-score | quality_score.py | 多因子加权评分 > 阈值 | roe, profit_yoy, debt_ratio, pe_ttm |

### D5: FinanceIndicator 模型不新增字段

**选择：** 不在 `FinanceIndicator` 模型中新增 `dividend_yield` 字段，估值指标通过管道实时查询 daily_basic。

**理由：**
- 避免 Alembic 迁移
- 估值指标每日变化，存在季度报表表中语义不对
- 管道查询 daily_basic 更准确

## Risks / Trade-offs

- **[性能] 管道增加一次 daily_basic 查询** → 查询量与股票数相当（~500 只），单次查询 <100ms，可接受
- **[数据] daily_basic 数据可能缺失** → 策略中对缺失值做 fillna 处理，缺失时不命中策略
- **[准确性] profit_continuous_growth 需要多期数据** → 当前 finance_indicator 按报告期存储，可查询最近 N 期；简化为只看最新一期的 profit_yoy > 0
- **[复杂度] quality-score 多因子评分** → 使用固定权重（ROE 30% + 增长 25% + 安全 25% + 估值 20%），不做动态优化
