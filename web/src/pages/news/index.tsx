import { useEffect, useState } from 'react'
import {
  Card, Col, DatePicker, Input, Row, Select, Space, Table, Tag, Tooltip,
} from 'antd'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import ReactECharts from 'echarts-for-react'
import { fetchNewsList, fetchSentimentSummary, fetchSentimentTrend } from '../../api/news'
import type {
  AnnouncementItem,
  SentimentTrendItem,
  SentimentSummaryItem,
} from '../../types/news'

export default function NewsPage() {
  // 新闻列表状态
  const [newsList, setNewsList] = useState<AnnouncementItem[]>([])
  const [newsTotal, setNewsTotal] = useState(0)
  const [newsPage, setNewsPage] = useState(1)
  const [newsLoading, setNewsLoading] = useState(false)
  const [filterCode, setFilterCode] = useState<string>()
  const [filterSource, setFilterSource] = useState<string>()

  // 情感趋势状态
  const [trendCode, setTrendCode] = useState('000001.SZ')
  const [trendData, setTrendData] = useState<SentimentTrendItem[]>([])
  const [trendLoading, setTrendLoading] = useState(false)

  // 每日摘要状态
  const [summaryDate, setSummaryDate] = useState<string>()
  const [summaryItems, setSummaryItems] = useState<SentimentSummaryItem[]>([])
  const [summaryLoading, setSummaryLoading] = useState(false)

  // 加载新闻列表
  const loadNews = async (p = newsPage) => {
    setNewsLoading(true)
    try {
      const res = await fetchNewsList({
        page: p,
        page_size: 20,
        ts_code: filterCode || undefined,
        source: filterSource || undefined,
      })
      setNewsList(res.items)
      setNewsTotal(res.total)
    } finally {
      setNewsLoading(false)
    }
  }

  // 加载情感趋势
  const loadTrend = async (code = trendCode) => {
    if (!code) return
    setTrendLoading(true)
    try {
      const res = await fetchSentimentTrend(code, 30)
      setTrendData(res)
    } finally {
      setTrendLoading(false)
    }
  }

  // 加载每日摘要
  const loadSummary = async (dt?: string) => {
    setSummaryLoading(true)
    try {
      const res = await fetchSentimentSummary(dt, 20)
      setSummaryItems(res.items)
      if (res.trade_date && !dt) setSummaryDate(res.trade_date)
    } finally {
      setSummaryLoading(false)
    }
  }

  useEffect(() => { loadNews() }, [newsPage, filterCode, filterSource])
  useEffect(() => { loadTrend() }, [trendCode])
  useEffect(() => { loadSummary(summaryDate) }, [summaryDate])

  // 情感标签颜色
  const labelColor = (label: string | null) => {
    if (label === '利好') return 'green'
    if (label === '利空') return 'red'
    if (label === '重大事件') return 'orange'
    return 'default'
  }

  // 新闻列表列定义
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

  // 摘要列定义
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

  // 情感趋势图配置
  const trendOption = {
    tooltip: { trigger: 'axis' as const },
    legend: { data: ['平均情感', '新闻数'] },
    xAxis: {
      type: 'category' as const,
      data: trendData.map((d) => d.trade_date),
    },
    yAxis: [
      { type: 'value' as const, name: '情感分数', min: -1, max: 1 },
      { type: 'value' as const, name: '新闻数' },
    ],
    series: [
      {
        name: '平均情感',
        type: 'line',
        data: trendData.map((d) => d.avg_sentiment),
        smooth: true,
        itemStyle: { color: '#1890ff' },
        markLine: {
          data: [
            { yAxis: 0.2, lineStyle: { color: '#52c41a', type: 'dashed' as const } },
            { yAxis: -0.2, lineStyle: { color: '#ff4d4f', type: 'dashed' as const } },
          ],
          silent: true,
          label: { show: false },
        },
      },
      {
        name: '新闻数',
        type: 'bar',
        yAxisIndex: 1,
        data: trendData.map((d) => d.news_count),
        itemStyle: { color: '#91caff', opacity: 0.5 },
      },
    ],
  }

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
            loading={trendLoading}
          >
            {trendData.length > 0 ? (
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
            <Table
              columns={summaryColumns}
              dataSource={summaryItems}
              rowKey="ts_code"
              size="small"
              loading={summaryLoading}
              pagination={false}
              scroll={{ y: 260 }}
            />
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
                { label: '淘股吧', value: 'taoguba' },
                { label: '雪球', value: 'xueqiu' },
              ]}
            />
          </Space>
        }
      >
        <Table
          columns={newsColumns}
          dataSource={newsList}
          rowKey="id"
          loading={newsLoading}
          pagination={{
            current: newsPage,
            total: newsTotal,
            pageSize: 20,
            onChange: (p) => setNewsPage(p),
            showTotal: (t) => `共 ${t} 条`,
          }}
          size="small"
        />
      </Card>
    </div>
  )
}
