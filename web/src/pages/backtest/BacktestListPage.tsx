import { Button, Table, Tag, Typography } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import type { ColumnsType } from 'antd/es/table'
import { fetchBacktestList } from '../../api/backtest'
import type { BacktestListItem } from '../../types'
import { useState } from 'react'

const { Text } = Typography

const statusMap: Record<string, { color: string; label: string }> = {
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '运行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
}

export default function BacktestListPage() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const pageSize = 20

  const { data, isLoading } = useQuery({
    queryKey: ['backtestList', page],
    queryFn: () => fetchBacktestList(page, pageSize),
  })

  const columns: ColumnsType<BacktestListItem> = [
    { title: 'ID', dataIndex: 'task_id', width: 60 },
    { title: '策略', dataIndex: 'strategy_name', width: 120 },
    { title: '股票数', dataIndex: 'stock_count', width: 80 },
    {
      title: '时间范围',
      width: 200,
      render: (_, r) => r.start_date && r.end_date ? `${r.start_date} ~ ${r.end_date}` : '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      width: 90,
      render: (v: string) => {
        const s = statusMap[v] ?? { color: 'default', label: v }
        return <Tag color={s.color}>{s.label}</Tag>
      },
    },
    {
      title: '年化收益率',
      dataIndex: 'annual_return',
      width: 110,
      render: (v: number | null) => {
        if (v == null) return '-'
        const pct = (v * 100).toFixed(2)
        return <Text type={v >= 0 ? 'danger' : 'success'}>{v >= 0 ? '+' : ''}{pct}%</Text>
      },
    },
    { title: '创建时间', dataIndex: 'created_at', width: 170 },
  ]

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>回测中心</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/backtest/new')}>
          新建回测
        </Button>
      </div>
      <Table<BacktestListItem>
        columns={columns}
        dataSource={data?.items ?? []}
        rowKey="task_id"
        loading={isLoading}
        size="small"
        pagination={{
          current: page,
          pageSize,
          total: data?.total ?? 0,
          onChange: setPage,
          showSizeChanger: false,
        }}
        onRow={(record) => ({
          onClick: () => navigate(`/backtest/${record.task_id}`),
          style: { cursor: 'pointer' },
        })}
      />
    </div>
  )
}
