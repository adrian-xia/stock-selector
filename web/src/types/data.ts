/** K 线数据条目 */
export interface KlineEntry {
  date: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

/** K 线查询响应 */
export interface KlineResponse {
  ts_code: string
  data: KlineEntry[]
}
