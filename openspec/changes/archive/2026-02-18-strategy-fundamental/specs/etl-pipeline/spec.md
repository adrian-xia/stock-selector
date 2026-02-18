## ADDED Requirements

### Requirement: 策略管道补充估值指标数据
策略管道的 `_enrich_finance_data()` SHALL 从 `raw_tushare_daily_basic` 表查询目标交易日的估值指标（pe_ttm、pb、ps_ttm、dv_ttm、total_mv、circ_mv），并合并到市场快照 DataFrame 中。

字段映射：
- `raw_tushare_daily_basic.pe_ttm` → DataFrame `pe_ttm`
- `raw_tushare_daily_basic.pb` → DataFrame `pb`
- `raw_tushare_daily_basic.ps_ttm` → DataFrame `ps_ttm`
- `raw_tushare_daily_basic.dv_ttm` → DataFrame `dividend_yield`
- `raw_tushare_daily_basic.total_mv` → DataFrame `total_mv`
- `raw_tushare_daily_basic.circ_mv` → DataFrame `circ_mv`

#### Scenario: 估值指标补充成功
- **WHEN** 策略管道执行 _enrich_finance_data()，目标日期为 2026-02-18
- **THEN** DataFrame 中 pe_ttm、pb、ps_ttm、dividend_yield、total_mv、circ_mv 列从 raw_tushare_daily_basic 填充

#### Scenario: daily_basic 数据缺失
- **WHEN** 某只股票在 raw_tushare_daily_basic 中无目标日期数据
- **THEN** 该股票的估值指标列为 NaN，不影响其他股票
