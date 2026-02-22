/**
 * 告警历史子组件。
 */
import { useEffect, useRef } from 'react'
import { Badge, Button, Card, notification, Table, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useQuery } from '@tanstack/react-query'
import { fetchAlertHistory } from '../../api/monitor'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type { AlertHistoryItem } from '../../types/monitor'

export default function AlertHistoryPanel() {
  const lastAlertIdRef = useRef(0)

  const historyQuery = useQuery({
    queryKey: ['alert-history'],
    queryFn: () => fetchAlertHistory({ page_size: 20 }),
    refetchInterval: 30_000,
  })

  // 新告警弹窗通知
  const items = historyQuery.data ?? []
  useEffect(() => {
    if (items.length > 0 && items[0].id > lastAlertIdRef.current) {
      if (lastAlertIdRef.current > 0) {
        notification.warning({ message: '新告警', description: items[0].message, duration: 5 })
      }
      lastAlertIdRef.current = items[0].id
    }
  }, [items])

  const historyColumns: ColumnsType<AlertHistoryItem> = [
    { title: '时间', dataIndex: 'triggered_at', key: 'triggered_at', width: 170 },
    { title: '股票', dataIndex: 'ts_code', key: 'ts_code', width: 110 },
    {
      title: '类型', dataIndex: 'rule_type', key: 'rule_type', width: 100,
      render: (v: string) => v === 'price_break' ? <Tag color="blue">价格</Tag> : <Tag color="purple">信号</Tag>,
    },
    { title: '消息', dataIndex: 'message', key: 'message' },
    {
      title: '通知', dataIndex: 'notified', key: 'notified', width: 60,
      render: (v: boolean) => v ? <Badge status="success" text="已发" /> : <Badge status="default" text="未发" />,
    },
  ]

  return (
    <Card
      title="告警历史（最近 20 条）"
      extra={<Button icon={<ReloadOutlined />} size="small" onClick={() => historyQuery.refetch()}>刷新</Button>}
    >
      {historyQuery.error ? (
        <QueryErrorAlert error={historyQuery.error} refetch={historyQuery.refetch} message="告警历史加载失败" />
      ) : (
        <Table columns={historyColumns} dataSource={items} rowKey="id" size="small"
          loading={historyQuery.isLoading} pagination={false} />
      )}
    </Card>
  )
}
