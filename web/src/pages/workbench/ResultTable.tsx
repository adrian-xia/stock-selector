import { Table, Tag, Typography } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import type { StockPick } from '../../types'

const { Text, Paragraph } = Typography

const signalColorMap: Record<string, string> = {
  STRONG_BUY: 'red',
  BUY: 'volcano',
  HOLD: 'default',
  SELL: 'green',
  STRONG_SELL: 'cyan',
}

interface Props {
  picks: StockPick[]
  loading: boolean
  aiEnabled: boolean
  onRowClick: (record: StockPick) => void
}

export default function ResultTable({ picks, loading, aiEnabled, onRowClick }: Props) {
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
      title: '匹配策略数',
      dataIndex: 'match_count',
      width: 100,
      sorter: (a, b) => a.match_count - b.match_count,
    },
    ...(aiEnabled
      ? [
          {
            title: 'AI 评分',
            dataIndex: 'ai_score' as const,
            width: 90,
            sorter: (a: StockPick, b: StockPick) => (a.ai_score ?? 0) - (b.ai_score ?? 0),
            render: (v: number | null) => v ?? '-',
          },
          {
            title: 'AI 信号',
            dataIndex: 'ai_signal' as const,
            width: 110,
            render: (v: string | null) => {
              if (!v) return '-'
              const color = signalColorMap[v] ?? 'default'
              return <Tag color={color}>{v}</Tag>
            },
          },
        ]
      : []),
  ]

  // AI 摘要展开行
  const expandable = aiEnabled
    ? {
        expandedRowRender: (record: StockPick) =>
          record.ai_summary ? (
            <Paragraph style={{ margin: 0 }}>{record.ai_summary}</Paragraph>
          ) : (
            <Text type="secondary">暂无 AI 分析摘要</Text>
          ),
        rowExpandable: (record: StockPick) => !!record.ai_score,
      }
    : undefined

  return (
    <Table<StockPick>
      columns={columns}
      dataSource={picks}
      rowKey="ts_code"
      loading={loading}
      size="small"
      pagination={{ pageSize: 20, showSizeChanger: false }}
      expandable={expandable}
      onRow={(record) => ({
        onClick: () => onRowClick(record),
        style: { cursor: 'pointer' },
      })}
    />
  )
}
