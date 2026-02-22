/**
 * 实时监控看板页面。
 *
 * 组合子组件：WatchlistTable、AlertRulePanel、AlertHistoryPanel。
 */
import { useEffect } from 'react'
import { Col, Row } from 'antd'
import { useWebSocket, type ConnectionStatus } from '../../hooks/useWebSocket'
import WatchlistTable from './WatchlistTable'
import AlertRulePanel from './AlertRulePanel'
import AlertHistoryPanel from './AlertHistoryPanel'

/** 连接状态 banner */
function StatusBanner({ status }: { status: ConnectionStatus }) {
  if (status === 'connected') return null
  return (
    <div
      style={{
        background: status === 'connecting' ? '#faad14' : '#ff4d4f',
        color: '#fff',
        textAlign: 'center',
        padding: '4px 0',
        fontSize: 13,
      }}
    >
      {status === 'connecting' ? '正在连接...' : '连接断开，5 秒后自动重连'}
    </div>
  )
}

export default function MonitorPage() {
  const { status, quotes, connect, disconnect, subscribe, unsubscribe } = useWebSocket()

  useEffect(() => {
    connect()
    return () => { disconnect() }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <StatusBanner status={status} />
      <WatchlistTable status={status} quotes={quotes} subscribe={subscribe} unsubscribe={unsubscribe} />
      <Row gutter={16}>
        <Col span={10}>
          <AlertRulePanel />
        </Col>
        <Col span={14}>
          <AlertHistoryPanel />
        </Col>
      </Row>
    </div>
  )
}
