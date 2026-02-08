/** 回测执行请求 */
export interface BacktestRunRequest {
  strategy_name: string
  strategy_params?: Record<string, number | string | boolean>
  stock_codes: string[]
  start_date: string
  end_date: string
  initial_capital?: number
}

/** 回测绩效指标 */
export interface BacktestMetrics {
  total_return: number | null
  annual_return: number | null
  max_drawdown: number | null
  sharpe_ratio: number | null
  win_rate: number | null
  profit_loss_ratio: number | null
  total_trades: number
  calmar_ratio: number | null
  sortino_ratio: number | null
  volatility: number | null
  elapsed_ms?: number
}

/** 回测执行响应 */
export interface BacktestRunResponse {
  task_id: number
  status: string
  result?: BacktestMetrics | null
  error_message?: string | null
}

/** 交易记录 */
export interface TradeEntry {
  stock_code: string
  direction: string
  date: string
  price: number
  size: number
  commission: number
  pnl: number
}

/** 净值曲线数据点 */
export interface EquityCurveEntry {
  date: string
  value: number
}

/** 回测结果详情响应 */
export interface BacktestResultResponse {
  task_id: number
  status: string
  strategy_name?: string | null
  stock_codes?: string[] | null
  start_date?: string | null
  end_date?: string | null
  result?: BacktestMetrics | null
  trades?: TradeEntry[] | null
  equity_curve?: EquityCurveEntry[] | null
  error_message?: string | null
}

/** 回测任务列表项 */
export interface BacktestListItem {
  task_id: number
  strategy_name: string
  stock_count: number
  start_date: string | null
  end_date: string | null
  status: string
  annual_return: number | null
  created_at: string
}

/** 回测任务列表响应 */
export interface BacktestListResponse {
  total: number
  page: number
  page_size: number
  items: BacktestListItem[]
}
