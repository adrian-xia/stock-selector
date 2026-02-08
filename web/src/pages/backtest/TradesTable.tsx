import { Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { TradeEntry } from '../../types'

interface Props {
  trades: TradeEntry[]
}

export default function TradesTable({ trades }: Props) {
  const columns: ColumnsType<TradeEntry> = [
    { title: '股票代码', dataIndex: 'stock_code', width: 110 },
    {
      title: '方向',
      dataIndex: 'direction',
      width: 80,
      render: (v: string) => (
        <Tag color={v === 'BUY' ? 'red' : 'green'}>
          {v === 'BUY' ? '买入' : '卖出'}
        </Tag>
      ),
    },
    { title: '日期', dataIndex: 'date', width: 110 },
    {
      title: '价格',
      dataIndex: 'price',
      width: 90,
      render: (v: number) => v.toFixed(2),
    },
    { title: '数量', dataIndex: 'size', width: 80 },
    {
      title: '手续费',
      dataIndex: 'commission',
      width: 90,
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '盈亏',
      dataIndex: 'pnl',
      width: 100,
      render: (v: number) => (
        <span style={{ color: v >= 0 ? '#cf1322' : '#3f8600' }}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}
        </span>
      ),
    },
  ]

  return (
    <Table<TradeEntry>
      columns={columns}
      dataSource={trades}
      rowKey={(_, i) => String(i)}
      size="small"
      pagination={{ pageSize: 20, showSizeChanger: false }}
    />
  )
}
