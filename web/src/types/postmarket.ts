/** 盘后链路结果相关类型定义 */

/** 每日选股汇总 */
export interface DailySummary {
  pick_date: string
  total_picks: number
  strategy_count: number
  avg_return_1d: number | null
  avg_return_5d: number | null
  hit_rate_5d: number | null
}

/** 单日选股明细 */
export interface DailyPickDetail {
  ts_code: string
  name: string | null
  strategy_name: string
  pick_score: number | null
  pick_close: number | null
  return_1d: number | null
  return_3d: number | null
  return_5d: number | null
  return_10d: number | null
  return_20d: number | null
  max_return: number | null
  max_drawdown: number | null
}

/** 盘后概览响应 */
export interface PostMarketOverview {
  recent_tasks: TaskExecutionItem[]
  hit_stats_summary: HitStatsSummaryItem[]
  latest_plans: LatestPlanItem[]
}

/** 任务执行日志 */
export interface TaskExecutionItem {
  task_type: string
  task_date: string | null
  status: string
  duration_ms: number | null
  error_message: string | null
  created_at: string | null
}

/** 命中率统计汇总 */
export interface HitStatsSummaryItem {
  strategy_name: string
  stat_date: string
  total_picks: number
  win_count: number
  hit_rate: number | null
  avg_return: number | null
}

/** 最新交易计划 */
export interface LatestPlanItem {
  ts_code: string
  trigger_type: string
  trigger_price: number | null
  stop_loss: number | null
  take_profit: number | null
  source_strategy: string
  confidence: number | null
}

/** 全市场优化请求 */
export interface MarketOptRunRequest {
  strategy_name: string
  param_space?: Record<string, { type: string; min: number; max: number; step: number }>
  lookback_days?: number
  auto_apply?: boolean
}

/** 全市场优化结果项 */
export interface MarketOptResultItem {
  rank: number
  params: Record<string, number>
  hit_rate_5d: number
  avg_return_5d: number
  max_drawdown: number
  total_picks: number
  score: number
}

/** 全市场优化任务 */
export interface MarketOptTask {
  id: number
  strategy_name: string
  status: string
  progress: number
  total_combinations: number | null
  completed_combinations: number
  best_params: Record<string, number> | null
  best_score: number | null
  auto_apply: boolean
  error_message: string | null
  created_at: string
  finished_at: string | null
}

/** 全市场优化结果响应 */
export interface MarketOptResultResponse {
  task_id: number
  status: string
  strategy_name: string
  progress: number
  best_params: Record<string, number> | null
  best_score: number | null
  results: MarketOptResultItem[]
  error_message: string | null
}
