import { useState } from 'react'
import {
    Card, Col, DatePicker, Progress, Row, Space, Statistic, Table, Tabs, Tag, Tooltip, Typography,
} from 'antd'
import {
    AlertOutlined,
    BarChartOutlined,
    DashboardOutlined,
    ExperimentOutlined,
    SafetyCertificateOutlined,
    ThunderboltOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import { fetchResearchOverview } from '../../api/research'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type { SectorItem, TradePlanItem } from '../../types/research'

const { Text, Title } = Typography

/** 风险偏好配色 */
function riskAppetiteTag(appetite: string) {
    const map: Record<string, { color: string; label: string }> = {
        high: { color: 'red', label: '高风险偏好' },
        mid: { color: 'orange', label: '中性' },
        low: { color: 'green', label: '低风险偏好' },
    }
    const { color, label } = map[appetite] ?? { color: 'default', label: appetite }
    return <Tag color={color}>{label}</Tag>
}

/** 市场状态标签 */
function regimeTag(regime: string) {
    const map: Record<string, { color: string; label: string }> = {
        bull: { color: '#cf1322', label: '🐂 牛市' },
        range: { color: '#d48806', label: '📊 震荡' },
        bear: { color: '#389e0d', label: '🐻 熊市' },
    }
    const { color, label } = map[regime] ?? { color: '#999', label: regime }
    return <Tag style={{ color, borderColor: color }}>{label}</Tag>
}

/** 计划状态标签 */
function planStatusTag(status: string) {
    const colorMap: Record<string, string> = {
        PENDING: 'blue', EXPIRED: 'default', EXECUTED: 'green', CANCELLED: 'red',
    }
    return <Tag color={colorMap[status] ?? 'default'}>{status}</Tag>
}

export default function ResearchPage() {
    const [tradeDate, setTradeDate] = useState(dayjs().format('YYYY-MM-DD'))

    const { data, isLoading, error, refetch } = useQuery({
        queryKey: ['research-overview', tradeDate],
        queryFn: () => fetchResearchOverview(tradeDate),
        staleTime: 60_000,
    })

    const macro = data?.macro_signal
    const sectors = data?.top_sectors ?? []
    const plans = data?.trade_plans ?? []

    // 行业共振表列
    const sectorColumns: ColumnsType<SectorItem> = [
        { title: '行业', dataIndex: 'sector_name', width: 120 },
        {
            title: '综合分', dataIndex: 'final_score', width: 90, sorter: (a, b) => a.final_score - b.final_score,
            render: (v: number) => <Text strong style={{ color: v >= 70 ? '#cf1322' : v >= 40 ? '#d48806' : '#666' }}>{v.toFixed(1)}</Text>,
        },
        {
            title: '新闻分', dataIndex: 'news_score', width: 80,
            render: (v: number) => <Progress percent={v} size="small" showInfo={false} strokeColor={v >= 60 ? '#52c41a' : '#faad14'} />,
        },
        {
            title: '资金分', dataIndex: 'moneyflow_score', width: 80,
            render: (v: number) => <Progress percent={v} size="small" showInfo={false} strokeColor={v >= 60 ? '#1890ff' : '#faad14'} />,
        },
        {
            title: '趋势分', dataIndex: 'trend_score', width: 80,
            render: (v: number) => <Progress percent={v} size="small" showInfo={false} strokeColor={v >= 60 ? '#722ed1' : '#faad14'} />,
        },
        {
            title: '置信度', dataIndex: 'confidence', width: 80,
            render: (v: number) => `${v.toFixed(0)}%`,
        },
        {
            title: '驱动因素', dataIndex: 'drivers', width: 140,
            render: (drivers: string[]) => drivers?.map((d, i) => <Tag key={i} color="geekblue" style={{ marginBottom: 2 }}>{d}</Tag>),
        },
    ]

    // 交易计划表列
    const planColumns: ColumnsType<TradePlanItem> = [
        { title: '代码', dataIndex: 'ts_code', width: 100 },
        { title: '策略来源', dataIndex: 'source_strategy', width: 130 },
        { title: '类型', dataIndex: 'plan_type', width: 80, render: (v: string) => <Tag>{v}</Tag> },
        { title: '状态', dataIndex: 'plan_status', width: 90, render: planStatusTag },
        {
            title: '市场状态', dataIndex: 'market_regime', width: 100,
            render: regimeTag,
        },
        {
            title: '仓位建议', dataIndex: 'position_suggestion', width: 90,
            render: (v: number) => `${(v * 100).toFixed(0)}%`,
        },
        {
            title: '置信度', dataIndex: 'confidence', width: 80,
            render: (v: number) => <Progress type="circle" percent={v} size={36} format={(p) => `${p?.toFixed(0)}`} />,
        },
        {
            title: '入场规则', dataIndex: 'entry_rule', ellipsis: true,
            render: (v: string) => <Tooltip title={v}><Text ellipsis>{v}</Text></Tooltip>,
        },
        {
            title: '止损', dataIndex: 'stop_loss_rule', width: 140, ellipsis: true,
        },
        {
            title: '风险标记', dataIndex: 'risk_flags', width: 140,
            render: (flags: string[]) => flags?.map((f, i) => <Tag key={i} color="volcano" style={{ marginBottom: 2 }}>{f}</Tag>),
        },
    ]

    return (
        <div>
            {/* 头部控件 */}
            <Space style={{ marginBottom: 16 }}>
                <ExperimentOutlined style={{ fontSize: 20, color: '#1890ff' }} />
                <Title level={4} style={{ margin: 0 }}>StarMap 投研总览</Title>
                <DatePicker
                    value={dayjs(tradeDate)}
                    onChange={(d) => d && setTradeDate(d.format('YYYY-MM-DD'))}
                    allowClear={false}
                    size="small"
                />
            </Space>

            {error ? (
                <QueryErrorAlert error={error} refetch={refetch} message="加载投研数据失败" />
            ) : (
                <>
                    {/* 宏观概览卡片 */}
                    <Row gutter={16} style={{ marginBottom: 16 }}>
                        <Col span={6}>
                            <Card loading={isLoading}>
                                <Statistic
                                    title="市场风险偏好"
                                    value={macro?.risk_appetite ?? '-'}
                                    prefix={<DashboardOutlined />}
                                    formatter={() => macro ? riskAppetiteTag(macro.risk_appetite) : '-'}
                                />
                            </Card>
                        </Col>
                        <Col span={6}>
                            <Card loading={isLoading}>
                                <Statistic
                                    title="全球风险评分"
                                    value={macro?.global_risk_score ?? 0}
                                    suffix="/ 100"
                                    prefix={<AlertOutlined />}
                                    valueStyle={{
                                        color: (macro?.global_risk_score ?? 50) >= 70 ? '#cf1322'
                                            : (macro?.global_risk_score ?? 50) >= 40 ? '#d48806' : '#3f8600',
                                    }}
                                />
                            </Card>
                        </Col>
                        <Col span={6}>
                            <Card loading={isLoading}>
                                <Statistic
                                    title="热门行业数"
                                    value={sectors.length}
                                    prefix={<BarChartOutlined />}
                                />
                            </Card>
                        </Col>
                        <Col span={6}>
                            <Card loading={isLoading}>
                                <Statistic
                                    title="交易计划数"
                                    value={plans.length}
                                    prefix={<ThunderboltOutlined />}
                                />
                            </Card>
                        </Col>
                    </Row>

                    {/* 宏观摘要 */}
                    {macro?.summary && (
                        <Card size="small" style={{ marginBottom: 16 }} title={<><SafetyCertificateOutlined /> 宏观摘要</>}>
                            <Text>{macro.summary}</Text>
                            {macro.positive_sectors.length > 0 && (
                                <div style={{ marginTop: 8 }}>
                                    <Text type="secondary">利好行业：</Text>
                                    {macro.positive_sectors.map((s, i) => <Tag key={i} color="green">{s}</Tag>)}
                                </div>
                            )}
                            {macro.negative_sectors.length > 0 && (
                                <div style={{ marginTop: 4 }}>
                                    <Text type="secondary">利空行业：</Text>
                                    {macro.negative_sectors.map((s, i) => <Tag key={i} color="red">{s}</Tag>)}
                                </div>
                            )}
                        </Card>
                    )}

                    {/* Tabs: 行业共振 + 交易计划 */}
                    <Card>
                        <Tabs
                            defaultActiveKey="sectors"
                            items={[
                                {
                                    key: 'sectors',
                                    label: `行业共振 (${sectors.length})`,
                                    children: (
                                        <Table
                                            rowKey="sector_code"
                                            columns={sectorColumns}
                                            dataSource={sectors}
                                            loading={isLoading}
                                            size="small"
                                            pagination={{ pageSize: 15 }}
                                            scroll={{ x: 800 }}
                                        />
                                    ),
                                },
                                {
                                    key: 'plans',
                                    label: `交易计划 (${plans.length})`,
                                    children: (
                                        <Table
                                            rowKey={(r) => `${r.ts_code}_${r.source_strategy}`}
                                            columns={planColumns}
                                            dataSource={plans}
                                            loading={isLoading}
                                            size="small"
                                            pagination={{ pageSize: 15 }}
                                            scroll={{ x: 1200 }}
                                        />
                                    ),
                                },
                            ]}
                        />
                    </Card>
                </>
            )}
        </div>
    )
}
