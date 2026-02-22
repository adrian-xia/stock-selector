/**
 * 自选股行情表格子组件。
 */
import { useEffect, useState } from 'react'
import {
  Badge, Button, Card, Input, Popconfirm, Space, Table,
} from 'antd'
import { DeleteOutlined, PlusOutlined, WifiOutlined, DisconnectOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchRealtimeStatus, addWatchlist, removeWatchlist } from '../../api/monitor'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type { ConnectionStatus, RealtimeQuote } from '../../hooks/useWebSocket'

interface Props {
  status: ConnectionStatus
  quotes: Map<string, RealtimeQuote>
  subscribe: (codes: string[]) => void
  unsubscribe: (codes: string[]) => void
}

/** 价格变动颜色 */
function priceColor(val?: number) {
  if (!val) return undefined
  return val > 0 ? '#cf1322' : val < 0 ? '#3f8600' : undefined
}

export default function WatchlistTable({ status, quotes, subscribe, unsubscribe }: Props) {
  const [addCode, setAddCode] = useState('')
  const queryClient = useQueryClient()

  const statusQuery = useQuery({
    queryKey: ['realtime-status'],
    queryFn: fetchRealtimeStatus,
  })

  const watchlist = statusQuery.data?.watchlist ?? []
  const maxStocks = statusQuery.data?.max_stocks ?? 50

  const addMutation = useMutation({
    mutationFn: (code: string) => addWatchlist([code]),
    onSuccess: (_data, code) => {
      subscribe([code])
      setAddCode('')
      queryClient.invalidateQueries({ queryKey: ['realtime-status'] })
    },
  })

  const removeMutation = useMutation({
    mutationFn: (code: string) => removeWatchlist([code]),
    onSuccess: (_data, code) => {
      unsubscribe([code])
      queryClient.invalidateQueries({ queryKey: ['realtime-status'] })
    },
  })

  // WebSocket 连接后自动订阅自选股
  useEffect(() => {
    if (status === 'connected' && watchlist.length > 0) {
      subscribe(watchlist)
    }
  }, [status, watchlist, subscribe])
  const handleAdd = () => {
    const code = addCode.trim().toUpperCase()
    if (!code) return
    addMutation.mutate(code)
  }

  const quoteColumns: ColumnsType<RealtimeQuote> = [
    { title: '代码', dataIndex: 'ts_code', key: 'ts_code', width: 110 },
    {
      title: '最新价', dataIndex: 'close', key: 'close', width: 90,
      render: (v: number, r: RealtimeQuote) => (
        <span style={{ color: priceColor(r.pct_chg), fontWeight: 600 }}>{v?.toFixed(2) ?? '-'}</span>
      ),
    },
    {
      title: '涨跌幅', dataIndex: 'pct_chg', key: 'pct_chg', width: 90,
      render: (v: number) => (
        <span style={{ color: priceColor(v) }}>{v != null ? `${v > 0 ? '+' : ''}${v.toFixed(2)}%` : '-'}</span>
      ),
    },
    { title: '开盘', dataIndex: 'open', key: 'open', width: 80, render: (v: number) => v?.toFixed(2) ?? '-' },
    { title: '最高', dataIndex: 'high', key: 'high', width: 80, render: (v: number) => v?.toFixed(2) ?? '-' },
    { title: '最低', dataIndex: 'low', key: 'low', width: 80, render: (v: number) => v?.toFixed(2) ?? '-' },
    { title: '成交量', dataIndex: 'vol', key: 'vol', width: 100, render: (v: number) => v != null ? `${(v / 100).toFixed(0)}手` : '-' },
    {
      title: '操作', key: 'action', width: 60,
      render: (_: unknown, r: RealtimeQuote) => (
        <Popconfirm title="确认移除？" onConfirm={() => removeMutation.mutate(r.ts_code)}>
          <Button type="link" size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ]

  const quoteData: RealtimeQuote[] = watchlist.map((code) => {
    const q = quotes.get(code)
    return q ?? { ts_code: code }
  })

  return (
    <Card
      title={
        <Space>
          <span>自选股行情</span>
          {status === 'connected'
            ? <Badge status="success" text={<span style={{ fontSize: 12 }}><WifiOutlined /> 已连接</span>} />
            : <Badge status="error" text={<span style={{ fontSize: 12 }}><DisconnectOutlined /> 未连接</span>} />}
        </Space>
      }
      extra={
        <Space>
          <Input
            placeholder="输入股票代码（如 600519.SH）"
            value={addCode}
            onChange={(e) => setAddCode(e.target.value)}
            onPressEnter={handleAdd}
            style={{ width: 220 }}
            disabled={watchlist.length >= maxStocks}
          />
          <Button icon={<PlusOutlined />} onClick={handleAdd}
            disabled={watchlist.length >= maxStocks} loading={addMutation.isPending}>
            添加
          </Button>
          <span style={{ fontSize: 12, color: '#999' }}>{watchlist.length}/{maxStocks}</span>
        </Space>
      }
    >
      {statusQuery.error ? (
        <QueryErrorAlert error={statusQuery.error} refetch={statusQuery.refetch} message="自选股加载失败" />
      ) : (
        <Table
          columns={quoteColumns}
          dataSource={quoteData}
          rowKey="ts_code"
          size="small"
          loading={statusQuery.isLoading}
          pagination={false}
          locale={{ emptyText: '暂无自选股，请添加股票代码' }}
        />
      )}
    </Card>
  )
}
