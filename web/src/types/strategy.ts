/** 策略元数据 */
export interface StrategyMeta {
  name: string
  display_name: string
  category: string
  role: string
  signal_group?: string | null
  description: string
  default_params: Record<string, number | string | boolean>
  param_space: Record<string, unknown>
  ai_rating: number
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

/** 策略配置（含启用状态和自定义参数） */
export interface StrategyConfig {
  name: string
  display_name: string
  category: string
  description: string
  default_params: Record<string, number>
  params: Record<string, number>
  is_enabled: boolean
}

/** 策略配置列表响应 */
export interface StrategyConfigListResponse {
  strategies: StrategyConfig[]
}

/** 选股执行请求 */
export interface StrategyRunRequest {
  strategy_names: string[]
  strategy_params?: Record<string, Record<string, number | string | boolean>>
  target_date?: string
  industries?: string[]
  markets?: string[]
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
  weighted_score: number
  quality_score: number
  tags: Record<string, number>
  triggered_signals: Array<{
    strategy: string
    group: string
    confidence: number
    weight: number
  }>
  confirmed_bonus: number
  dynamic_weight: number
  style_bonus: number
  final_score: number
  market_regime: string
}

/** 选股执行响应 */
export interface StrategyRunResponse {
  target_date: string
  total_picks: number
  elapsed_ms: number
  layer_stats: Record<string, number>
  market_regime: string
  ai_enabled: boolean
  picks: StockPick[]
}
