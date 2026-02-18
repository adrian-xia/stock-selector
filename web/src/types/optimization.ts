/** 参数优化相关类型定义 */

export interface ParamSpec {
  type: 'int' | 'float'
  min: number
  max: number
  step: number
}

export type ParamSpace = Record<string, ParamSpec>

export interface OptimizationRunRequest {
  strategy_name: string
  algorithm: 'grid' | 'genetic'
  param_space?: ParamSpace
  stock_codes: string[]
  start_date: string
  end_date: string
  initial_capital?: number
  ga_config?: Record<string, number>
  top_n?: number
}

export interface OptimizationRunResponse {
  task_id: number
  status: string
  error_message?: string
}

export interface OptimizationResultItem {
  rank: number
  params: Record<string, number>
  sharpe_ratio: number | null
  annual_return: number | null
  max_drawdown: number | null
  win_rate: number | null
  total_trades: number | null
  total_return: number | null
  volatility: number | null
  calmar_ratio: number | null
  sortino_ratio: number | null
}

export interface OptimizationResultResponse {
  task_id: number
  status: string
  strategy_name: string | null
  algorithm: string | null
  progress: number
  total_combinations: number | null
  completed_combinations: number
  results: OptimizationResultItem[]
  error_message: string | null
}

export interface OptimizationListItem {
  task_id: number
  strategy_name: string
  algorithm: string
  status: string
  progress: number
  total_combinations: number | null
  created_at: string
}

export interface OptimizationListResponse {
  total: number
  page: number
  page_size: number
  items: OptimizationListItem[]
}

export interface ParamSpaceResponse {
  strategy_name: string
  display_name: string
  default_params: Record<string, number>
  param_space: ParamSpace
}
