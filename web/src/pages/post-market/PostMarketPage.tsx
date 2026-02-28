import { useState } from 'react'
import { Card, Col, InputNumber, Row, Space, Statistic, Table, Tabs, Tag } from 'antd'
import {
  CheckCircleOutlined,
  CloseCircleOutlined,
  StockOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useQuery } from '@tanstack/react-query'
import { fetchPostMarketOverview, fetchDailySummary } from '../../api/postmarket'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type {
  TaskExecutionItem,
  HitStatsSummaryItem,
  LatestPlanItem,
} from '../../types/postmarket'

export default function PostMarketPage() {
  const [days, setDays] = useState(7)

  // 盘后概览
  const overviewQuery = useQuery({
    queryKey: ['post-market-overview', days],
    queryFn: () => fetchPostMarketOverview(days),
    staleTime: 60_000,
  })

  // 最近汇总（用于统计卡片）
  const summaryQuery = useQuery({
    queryKey: ['daily-summary', 7],
    queryFn: () => fetchDailySummary(7),
    staleTime: 60_000,
  })

  const overview = overviewQuery.data
  const latestSummary = summaryQuery.data?.[0]

  // 任务执行日志列
  const taskColumns: ColumnsType<TaskExecutionItem> = [
    { title: '任务类型', dataIndex: 'task_type', width: 140 },
    { title: '日期', dataIndex: 'task_date', width: 110 },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => (
        <Tag color={v === 'success' ? 'green' : v === 'failed' ? 'red' : 'blue'}>{v}</Tag>
      ),
    },
    {
      title: '耗时', dataIndex: 'duration_ms', width: 90,
      render: (v: number | null) => v != null ? `${(v / 1000).toFixed(1)}s` : '-',
    },
    { title: '错误', dataIndex: 'error_message', ellipsis: true },
    { title: '执行时间', dataIndex: 'created_at', width: 160 },
  ]

  // 命中率列
  const hitColumns: ColumnsType<HitStatsSummaryItem> = [
    { title: '策略', dataIndex: 'strategy_name', width: 160 },
    { title: '统计日期', dataIndex: 'stat_date', width: 110 },
    { title: '总选股', dataIndex: 'total_picks', width: 80 },
    { title: '命中数', dataIndex: 'win_count', width: 80 },
    {
      title: '5d命中率', dataIndex: 'hit_rate', width: 100,
      render: (v: number | null) => {
        if (v == null) return '-'
        const pct = (v * 100).toFixed(1)
        const color = v >= 0.6 ? 'green' : v >= 0.4 ? 'orange' : 'red'
        return <Tag color={color}>{pct}%</Tag>
      },
    },
    {
      title: '平均收益', dataIndex: 'avg_return', width: 100,
      render: (v: number | null) => {
        if (v == null) return '-'
        const pct = (v * 100).toFixed(2)
        const color = v > 0 ? '#cf1322' : v < 0 ? '#3f8600' : undefined
        return <span style={{ color }}>{v > 0 ? '+' : ''}{pct}%</span>
      },
    },
  ]

  // 交易计划列
  const planColumns: ColumnsType<LatestPlanItem> = [
    { title: '代码', dataIndex: 'ts_code', width: 100 },
    { title: '触发类型', dataIndex: 'trigger_type', width: 100 },
    {
      title: '触发价', dataIndex: 'trigger_price', width: 90,
      render: (v: number | null) => v?.toFixed(2) ?? '-',
    },
    {
      title: '止损', dataIndex: 'stop_loss', width: 90,
      render: (v: number | null) => v?.toFixed(2) ?? '-',
    },
    {
      title: '止盈', dataIndex: 'take_profit', width: 90,
      render: (v: number | null) => v?.toFixed(2) ?? '-',
    },
    { title: '来源策略', dataIndex: 'source_strategy', width: 140 },
    {
      title: '置信度', dataIndex: 'confidence', width: 80,
      render: (v: number | null) => v != null ? `${(v * 100).toFixed(0)}%` : '-',
    },
  ]

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日选股数"
              value={latestSummary?.total_picks ?? 0}
              prefix={<StockOutlined />}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="5日命中率"
              value={latestSummary?.hit_rate_5d != null ? (latestSummary.hit_rate_5d * 100) : 0}
              suffix="%"
              precision={1}
              prefix={latestSummary?.hit_rate_5d != null && latestSummary.hit_rate_5d >= 0.5
                ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
              valueStyle={{ color: latestSummary?.hit_rate_5d != null && latestSummary.hit_rate_5d >= 0.5 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="5日均收益"
              value={latestSummary?.avg_return_5d != null ? (latestSummary.avg_return_5d * 100) : 0}
              suffix="%"
              precision={2}
              valueStyle={{ color: (latestSummary?.avg_return_5d ?? 0) >= 0 ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="交易计划数"
              value={overview?.latest_plans?.length ?? 0}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* 主内容 Tabs */}
      <Card
        title="盘后链路概览"
        extra={
          <Space>
            <span>最近</span>
            <InputNumber
              min={1} max={90} value={days}
              onChange={(v) => v && setDays(v)}
              style={{ width: 80 }}
              size="small"
            />
            <span>天</span>
          </Space>
        }
      >
        {overviewQuery.error ? (
          <QueryErrorAlert error={overviewQuery.error} refetch={overviewQuery.refetch} message="加载失败" />
        ) : (
          <Tabs
            defaultActiveKey="tasks"
            items={[
              {
                key: 'tasks',
                label: '任务执行日志',
                children: (
                  <Table
                    rowKey={(r, i) => `${r.task_type}_${r.created_at}_${i}`}
                    columns={taskColumns}
                    dataSource={overview?.recent_tasks ?? []}
                    loading={overviewQuery.isLoading}
                    size="small"
                    pagination={{ pageSize: 10 }}
                  />
                ),
              },
              {
                key: 'hits',
                label: '命中率统计',
                children: (
                  <Table
                    rowKey="strategy_name"
                    columns={hitColumns}
                    dataSource={overview?.hit_stats_summary ?? []}
                    loading={overviewQuery.isLoading}
                    size="small"
                    pagination={false}
                  />
                ),
              },
              {
                key: 'plans',
                label: '最新交易计划',
                children: (
                  <Table
                    rowKey="ts_code"
                    columns={planColumns}
                    dataSource={overview?.latest_plans ?? []}
                    loading={overviewQuery.isLoading}
                    size="small"
                    pagination={false}
                  />
                ),
              },
            ]}
          />
        )}
      </Card>
    </div>
  )
}
