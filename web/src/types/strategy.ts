/** 策略元数据 */
export interface StrategyMeta {
  name: string
  display_name: string
  category: string
  description: string
  default_params: Record<string, number | string | boolean>
}

/** 策略列表响应 */
export interface StrategyListResponse {
  strategies: StrategyMeta[]
}

/** 策略参数 schema 响应 */
export interface StrategySchemaResponse {
  name: string
  display_name: string
  default_params: Record<string, number | string | boolean>
}

/** 选股执行请求 */
export interface StrategyRunRequest {
  strategy_names: string[]
  target_date?: string
  base_filter?: {
    exclude_st?: boolean
    exclude_halt?: boolean
  }
  top_n?: number
}

/** 单只股票选股结果 */
export interface StockPick {
  ts_code: string
  name: string
  close: number
  pct_chg: number
  matched_strategies: string[]
  match_count: number
  ai_score?: number | null
  ai_signal?: string | null
  ai_summary?: string | null
}

/** 选股执行响应 */
export interface StrategyRunResponse {
  target_date: string
  total_picks: number
  elapsed_ms: number
  layer_stats: Record<string, number>
  ai_enabled: boolean
  picks: StockPick[]
}
