import { useState } from 'react'
import { Card, InputNumber, Space, Table, Tag } from 'antd'
import type { ColumnsType } from 'antd/es/table'
import { useQuery } from '@tanstack/react-query'
import { fetchDailySummary, fetchPicksByDate } from '../../api/postmarket'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type { DailySummary, DailyPickDetail } from '../../types/postmarket'

/** 收益率渲染：正数绿色、负数红色 */
function renderReturn(v: number | null) {
  if (v == null) return '-'
  const pct = (v * 100).toFixed(2)
  const color = v > 0 ? '#cf1322' : v < 0 ? '#3f8600' : undefined
  return <span style={{ color }}>{v > 0 ? '+' : ''}{pct}%</span>
}

export default function DailyPicksPage() {
  const [days, setDays] = useState(30)
  const [expandedDate, setExpandedDate] = useState<string | null>(null)

  // 每日汇总
  const summaryQuery = useQuery({
    queryKey: ['daily-summary', days],
    queryFn: () => fetchDailySummary(days),
    staleTime: 60_000,
  })

  // 展开行明细
  const detailQuery = useQuery({
    queryKey: ['picks-by-date', expandedDate],
    queryFn: () => fetchPicksByDate(expandedDate!),
    enabled: !!expandedDate,
    staleTime: 60_000,
  })

  const summaryColumns: ColumnsType<DailySummary> = [
    { title: '日期', dataIndex: 'pick_date', width: 120 },
    { title: '选股数', dataIndex: 'total_picks', width: 80 },
    { title: '策略数', dataIndex: 'strategy_count', width: 80 },
    {
      title: '1日均收益', dataIndex: 'avg_return_1d', width: 110,
      render: renderReturn,
    },
    {
      title: '5日均收益', dataIndex: 'avg_return_5d', width: 110,
      render: renderReturn,
    },
    {
      title: '5日命中率', dataIndex: 'hit_rate_5d', width: 110,
      render: (v: number | null) => {
        if (v == null) return '-'
        const pct = (v * 100).toFixed(1)
        const color = v >= 0.6 ? 'green' : v >= 0.4 ? 'orange' : 'red'
        return <Tag color={color}>{pct}%</Tag>
      },
    },
  ]

  const detailColumns: ColumnsType<DailyPickDetail> = [
    { title: '代码', dataIndex: 'ts_code', width: 100 },
    { title: '名称', dataIndex: 'name', width: 90 },
    { title: '策略', dataIndex: 'strategy_name', width: 140 },
    { title: '买入价', dataIndex: 'pick_close', width: 80,
      render: (v: number | null) => v?.toFixed(2) ?? '-' },
    { title: '1d', dataIndex: 'return_1d', width: 80, render: renderReturn },
    { title: '3d', dataIndex: 'return_3d', width: 80, render: renderReturn },
    { title: '5d', dataIndex: 'return_5d', width: 80, render: renderReturn },
    { title: '10d', dataIndex: 'return_10d', width: 80, render: renderReturn },
    { title: '20d', dataIndex: 'return_20d', width: 80, render: renderReturn },
    { title: '最大涨幅', dataIndex: 'max_return', width: 90, render: renderReturn },
    { title: '最大回撤', dataIndex: 'max_drawdown', width: 90, render: renderReturn },
  ]

  return (
    <div>
      <Card
        title="每日选股结果"
        extra={
          <Space>
            <span>最近</span>
            <InputNumber
              min={1} max={365} value={days}
              onChange={(v) => v && setDays(v)}
              style={{ width: 80 }}
              size="small"
            />
            <span>天</span>
          </Space>
        }
      >
        {summaryQuery.error ? (
          <QueryErrorAlert error={summaryQuery.error} refetch={summaryQuery.refetch} message="加载失败" />
        ) : (
          <Table
            rowKey="pick_date"
            columns={summaryColumns}
            dataSource={summaryQuery.data ?? []}
            loading={summaryQuery.isLoading}
            size="small"
            pagination={{ pageSize: 15 }}
            expandable={{
              expandedRowKeys: expandedDate ? [expandedDate] : [],
              onExpand: (expanded, record) => {
                setExpandedDate(expanded ? record.pick_date : null)
              },
              expandedRowRender: () => (
                <Table
                  rowKey={(r) => `${r.ts_code}_${r.strategy_name}`}
                  columns={detailColumns}
                  dataSource={detailQuery.data ?? []}
                  loading={detailQuery.isLoading}
                  size="small"
                  pagination={false}
                  scroll={{ y: 400 }}
                />
              ),
            }}
          />
        )}
      </Card>
    </div>
  )
}
