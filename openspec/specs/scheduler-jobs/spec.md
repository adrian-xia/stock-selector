## MODIFIED Requirements

### Requirement: _build_manager 使用 TushareClient
_build_manager() SHALL 创建 TushareClient 实例替代 BaoStockClient + AKShareClient，不再需要 BaoStock 连接池。

#### Scenario: 构建 DataManager
- **WHEN** 调用 _build_manager()
- **THEN** 返回使用 TushareClient 的 DataManager 实例，primary="tushare"

### Requirement: 盘后链路适配按日期同步
run_post_market_chain SHALL 使用按日期全市场同步模式。在批量数据拉取（步骤 3）之后、缓存刷新（步骤 4）之前，依次增加资金流向同步步骤（步骤 3.5）、指数数据同步步骤（步骤 3.6）、板块数据同步步骤（步骤 3.7）和 P5 核心数据同步步骤（步骤 3.8）。资金流向、指数数据、板块数据和 P5 核心数据同步失败不阻断后续链路。

#### Scenario: 盘后链路执行
- **WHEN** 盘后链路触发（交易日 15:30）
- **THEN** 执行：交易日历 → 股票列表 → 批量数据拉取 → **资金流向同步** → **指数数据同步** → **板块数据同步** → **P5 核心数据同步** → 缓存刷新 → 完整性门控 → 策略

#### Scenario: 同步性能提升
- **WHEN** 盘后链路执行全市场日线同步
- **THEN** 仅需 3-4 次 API 调用（vs 旧方案 ~5000 次），耗时从数十分钟降至数秒

#### Scenario: 资金流向同步失败不阻断
- **WHEN** 资金流向同步步骤抛出异常
- **THEN** 记录错误日志，继续执行缓存刷新和策略管道

#### Scenario: 指数数据同步失败不阻断
- **WHEN** 指数数据同步步骤抛出异常
- **THEN** 记录错误日志，继续执行缓存刷新和策略管道

#### Scenario: 板块数据同步失败不阻断
- **WHEN** 板块数据同步步骤抛出异常
- **THEN** 记录错误日志，继续执行缓存刷新和策略管道

#### Scenario: P5 核心数据同步失败不阻断
- **WHEN** P5 核心数据同步步骤抛出异常
- **THEN** 记录错误日志，继续执行缓存刷新和策略管道

### Requirement: 盘后链路增加 AI 分析步骤
run_post_market_chain SHALL 在策略管道执行后增加 AI 分析步骤（步骤 6.5），对 Top 30 候选股进行 AI 分析并持久化结果。AI 分析失败不阻断后续链路。

#### Scenario: 盘后 AI 分析执行
- **WHEN** 策略管道执行完成且产出候选股
- **THEN** 取 Top 30 候选股调用 AI 分析，结果写入 ai_analysis_results 表

#### Scenario: AI 分析失败不阻断
- **WHEN** AI 分析步骤抛出异常
- **THEN** 记录错误日志，盘后链路继续完成

#### Scenario: 无候选股时跳过
- **WHEN** 策略管道未产出候选股
- **THEN** 跳过 AI 分析步骤，记录日志
