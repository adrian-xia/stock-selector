/** 实时监控相关类型定义 */

export interface AlertRule {
  id: number
  ts_code: string
  rule_type: string
  params: Record<string, unknown>
  enabled: boolean
  cooldown_minutes: number
  last_triggered_at: string | null
  created_at: string
}

export interface AlertRuleCreate {
  ts_code: string
  rule_type: string
  params?: Record<string, unknown>
  cooldown_minutes?: number
}

export interface AlertRuleUpdate {
  enabled?: boolean
  params?: Record<string, unknown>
  cooldown_minutes?: number
}

export interface AlertHistoryItem {
  id: number
  rule_id: number
  ts_code: string
  rule_type: string
  message: string
  notified: boolean
  triggered_at: string
}

export interface RealtimeStatus {
  collecting: boolean
  watchlist_count: number
  watchlist: string[]
  websocket_connections: number
  max_stocks: number
}
