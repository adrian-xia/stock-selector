import { Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { StockPick } from '../../types'

const { Text } = Typography

interface Props {
  picks: StockPick[]
  loading: boolean
  onRowClick: (record: StockPick) => void
}

export default function ResultTable({ picks, loading, onRowClick }: Props) {
  const columns: ColumnsType<StockPick> = [
    {
      title: '代码',
      dataIndex: 'ts_code',
      width: 110,
    },
    {
      title: '名称',
      dataIndex: 'name',
      width: 90,
    },
    {
      title: '现价',
      dataIndex: 'close',
      width: 80,
      sorter: (a, b) => a.close - b.close,
      render: (v: number) => v.toFixed(2),
    },
    {
      title: '涨跌幅',
      dataIndex: 'pct_chg',
      width: 90,
      sorter: (a, b) => a.pct_chg - b.pct_chg,
      render: (v: number) => (
        <Text type={v >= 0 ? 'danger' : 'success'}>
          {v >= 0 ? '+' : ''}{v.toFixed(2)}%
        </Text>
      ),
    },
    {
      title: '触发数',
      dataIndex: 'match_count',
      width: 100,
      sorter: (a, b) => a.match_count - b.match_count,
    },
    {
      title: '质量分',
      dataIndex: 'quality_score',
      width: 90,
      sorter: (a, b) => a.quality_score - b.quality_score,
      render: (v: number) => v.toFixed(1),
    },
    {
      title: '综合分',
      dataIndex: 'final_score',
      width: 100,
      sorter: (a, b) => a.final_score - b.final_score,
      render: (v: number) => v.toFixed(3),
    },
    {
      title: '风格',
      dataIndex: 'tags',
      width: 160,
      render: (tags: StockPick['tags']) => {
        const entries = Object.entries(tags ?? {})
        if (!entries.length) return '-'
        return entries.map(([key, value]) => (
          <Tag key={key}>{key}:{value.toFixed(2)}</Tag>
        ))
      },
    },
  ]

  return (
    <Table<StockPick>
      columns={columns}
      dataSource={picks}
      rowKey="ts_code"
      loading={loading}
      size="small"
      pagination={{ pageSize: 20, showSizeChanger: false }}
      onRow={(record) => ({
        onClick: () => onRowClick(record),
        style: { cursor: 'pointer' },
      })}
    />
  )
}
