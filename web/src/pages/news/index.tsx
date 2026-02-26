import { useState } from 'react'
import {
  Card, Col, DatePicker, Input, Row, Select, Space, Table, Tag,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import ReactECharts from 'echarts-for-react'
import { useQuery } from '@tanstack/react-query'
import { fetchNewsList, fetchSentimentSummary, fetchSentimentTrend } from '../../api/news'
import { mergeChartOption } from '../../utils/chartTheme'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type {
  AnnouncementItem,
  SentimentSummaryItem,
} from '../../types/news'

export default function NewsPage() {
  // 筛选状态
  const [newsPage, setNewsPage] = useState(1)
  const [filterCode, setFilterCode] = useState<string>()
  const [filterSource, setFilterSource] = useState<string>()
  const [trendCode, setTrendCode] = useState('000001.SZ')
  const [summaryDate, setSummaryDate] = useState<string>()

  // 新闻列表
  const newsQuery = useQuery({
    queryKey: ['news-list', newsPage, filterCode, filterSource],
    queryFn: () => fetchNewsList({
      page: newsPage, page_size: 20,
      ts_code: filterCode || undefined,
      source: filterSource || undefined,
    }),
  })

  // 情感趋势
  const trendQuery = useQuery({
    queryKey: ['sentiment-trend', trendCode],
    queryFn: () => fetchSentimentTrend(trendCode, 30),
    enabled: !!trendCode,
  })

  // 每日摘要
  const summaryQuery = useQuery({
    queryKey: ['sentiment-summary', summaryDate],
    queryFn: () => fetchSentimentSummary(summaryDate, 20),
  })
  // 情感标签颜色
  const labelColor = (label: string | null) => {
    if (label === '利好') return 'green'
    if (label === '利空') return 'red'
    if (label === '重大事件') return 'orange'
    return 'default'
  }

  const newsColumns: ColumnsType<AnnouncementItem> = [
    { title: '股票代码', dataIndex: 'ts_code', width: 110 },
    {
      title: '标题', dataIndex: 'title', ellipsis: true,
      render: (text: string, record) =>
        record.url ? <a href={record.url} target="_blank" rel="noreferrer">{text}</a> : text,
    },
    { title: '来源', dataIndex: 'source', width: 80 },
    { title: '日期', dataIndex: 'pub_date', width: 110 },
    {
      title: '情感', dataIndex: 'sentiment_label', width: 90,
      render: (label: string | null) => label ? <Tag color={labelColor(label)}>{label}</Tag> : '-',
    },
    {
      title: '分数', dataIndex: 'sentiment_score', width: 80,
      render: (v: number | null) => v !== null ? v.toFixed(4) : '-',
    },
  ]

  const summaryColumns: ColumnsType<SentimentSummaryItem> = [
    { title: '股票代码', dataIndex: 'ts_code', width: 110 },
    {
      title: '平均情感', dataIndex: 'avg_sentiment', width: 100,
      render: (v: number) => {
        const color = v > 0.2 ? 'green' : v < -0.2 ? 'red' : undefined
        return <span style={{ color }}>{v.toFixed(4)}</span>
      },
    },
    { title: '新闻数', dataIndex: 'news_count', width: 80 },
    { title: '利好', dataIndex: 'positive_count', width: 60 },
    { title: '利空', dataIndex: 'negative_count', width: 60 },
    { title: '中性', dataIndex: 'neutral_count', width: 60 },
  ]

  const trendData = trendQuery.data ?? []
  const trendOption = mergeChartOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['平均情感', '新闻数'] },
    xAxis: { type: 'category', data: trendData.map((d) => d.trade_date) },
    yAxis: [
      { type: 'value', name: '情感分数', min: -1, max: 1 },
      { type: 'value', name: '新闻数' },
    ],
    series: [
      {
        name: '平均情感', type: 'line', data: trendData.map((d) => d.avg_sentiment),
        smooth: true, itemStyle: { color: '#1890ff' },
        markLine: {
          data: [
            { yAxis: 0.2, lineStyle: { color: '#52c41a', type: 'dashed' as const } },
            { yAxis: -0.2, lineStyle: { color: '#ff4d4f', type: 'dashed' as const } },
          ],
          silent: true, label: { show: false },
        },
      },
      {
        name: '新闻数', type: 'bar', yAxisIndex: 1,
        data: trendData.map((d) => d.news_count),
        itemStyle: { color: '#91caff', opacity: 0.5 },
      },
    ],
  })
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* 情感趋势图 + 每日摘要 */}
      <Row gutter={16}>
        <Col span={14}>
          <Card
            title="情感趋势"
            extra={
              <Input.Search
                placeholder="输入股票代码"
                defaultValue={trendCode}
                onSearch={(v) => setTrendCode(v.trim())}
                style={{ width: 200 }}
                allowClear
              />
            }
          >
            {trendQuery.error ? (
              <QueryErrorAlert error={trendQuery.error} refetch={trendQuery.refetch} />
            ) : trendData.length > 0 ? (
              <ReactECharts option={trendOption} style={{ height: 300 }} />
            ) : (
              <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无数据</div>
            )}
          </Card>
        </Col>
        <Col span={10}>
          <Card
            title="每日情感摘要"
            extra={
              <DatePicker
                value={summaryDate ? dayjs(summaryDate) : undefined}
                onChange={(d) => setSummaryDate(d?.format('YYYY-MM-DD'))}
                allowClear
                placeholder="选择日期"
              />
            }
          >
            {summaryQuery.error ? (
              <QueryErrorAlert error={summaryQuery.error} refetch={summaryQuery.refetch} />
            ) : (
              <Table
                columns={summaryColumns}
                dataSource={summaryQuery.data?.items ?? []}
                rowKey="ts_code"
                size="small"
                loading={summaryQuery.isLoading}
                pagination={false}
                scroll={{ y: 260 }}
              />
            )}
          </Card>
        </Col>
      </Row>

      {/* 新闻列表 */}
      <Card
        title="新闻列表"
        extra={
          <Space>
            <Input.Search
              placeholder="股票代码"
              onSearch={(v) => { setFilterCode(v.trim() || undefined); setNewsPage(1) }}
              style={{ width: 160 }}
              allowClear
            />
            <Select
              placeholder="来源"
              allowClear
              style={{ width: 120 }}
              onChange={(v) => { setFilterSource(v); setNewsPage(1) }}
              options={[
                { label: '东方财富', value: 'eastmoney' },
                { label: '新浪快讯', value: 'sina' },
                { label: '同花顺', value: 'ths' },
              ]}
            />
          </Space>
        }
      >
        {newsQuery.error ? (
          <QueryErrorAlert error={newsQuery.error} refetch={newsQuery.refetch} />
        ) : (
          <Table
            columns={newsColumns}
            dataSource={newsQuery.data?.items ?? []}
            rowKey="id"
            loading={newsQuery.isLoading}
            pagination={{
              current: newsPage,
              total: newsQuery.data?.total ?? 0,
              pageSize: 20,
              onChange: (p) => setNewsPage(p),
              showTotal: (t) => `共 ${t} 条`,
            }}
            size="small"
          />
        )}
      </Card>
    </div>
  )
}
