import { useCallback, useEffect, useRef, useState } from 'react'

export type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

export interface RealtimeQuote {
  ts_code: string
  trade_date?: string
  open?: number
  high?: number
  low?: number
  close?: number
  pre_close?: number
  change?: number
  pct_chg?: number
  vol?: number
  amount?: number
  [key: string]: unknown
}

interface WsMessage {
  type?: string
  ts_codes?: string[]
  message?: string
  [key: string]: unknown
}

const RECONNECT_DELAY = 5000

/**
 * WebSocket 实时行情 hook。
 * 自动重连、订阅管理、心跳响应。
 */
export function useWebSocket() {
  const [status, setStatus] = useState<ConnectionStatus>('disconnected')
  const [quotes, setQuotes] = useState<Map<string, RealtimeQuote>>(new Map())
  const wsRef = useRef<WebSocket | null>(null)
  const subscribedRef = useRef<Set<string>>(new Set())
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/realtime`)
    wsRef.current = ws
    setStatus('connecting')

    ws.onopen = () => {
      setStatus('connected')
      // 重连后恢复订阅
      if (subscribedRef.current.size > 0) {
        ws.send(JSON.stringify({ action: 'subscribe', ts_codes: [...subscribedRef.current] }))
      }
    }

    ws.onmessage = (event) => {
      try {
        const data: WsMessage = JSON.parse(event.data)
        if (data.type === 'ping') return
        if (data.type === 'error' || data.type === 'subscribed' || data.type === 'unsubscribed') return
        // 行情数据
        if (data.ts_code) {
          setQuotes((prev) => {
            const next = new Map(prev)
            next.set(data.ts_code as string, data as RealtimeQuote)
            return next
          })
        }
      } catch {
        // 忽略解析错误
      }
    }

    ws.onclose = () => {
      setStatus('disconnected')
      wsRef.current = null
      // 自动重连
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY)
    }

    ws.onerror = () => {
      ws.close()
    }
  }, [])

  const disconnect = useCallback(() => {
    clearTimeout(reconnectTimer.current)
    wsRef.current?.close()
    wsRef.current = null
    setStatus('disconnected')
  }, [])

  const subscribe = useCallback((tsCodes: string[]) => {
    tsCodes.forEach((c) => subscribedRef.current.add(c))
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'subscribe', ts_codes: tsCodes }))
    }
  }, [])

  const unsubscribe = useCallback((tsCodes: string[]) => {
    tsCodes.forEach((c) => subscribedRef.current.delete(c))
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ action: 'unsubscribe', ts_codes: tsCodes }))
    }
  }, [])

  useEffect(() => {
    return () => {
      clearTimeout(reconnectTimer.current)
      wsRef.current?.close()
    }
  }, [])

  return { status, quotes, connect, disconnect, subscribe, unsubscribe }
}
