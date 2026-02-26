import { useState, useMemo } from 'react'
import {
  Card, Switch, Table, Tag, InputNumber, Button, Space, message, Collapse, Badge,
} from 'antd'
import { SaveOutlined, UndoOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchStrategyConfigs, batchUpdateStrategyConfig } from '../../api/strategyConfig'
import QueryErrorAlert from '../../components/common/QueryErrorAlert'
import type { StrategyConfig } from '../../types/strategy'

/** 本地编辑状态：在原始配置基础上叠加用户修改 */
interface LocalEdit {
  is_enabled?: boolean
  params?: Record<string, number>
}

export default function StrategyConfigPage() {
  const queryClient = useQueryClient()
  // 本地编辑缓冲：name -> LocalEdit
  const [edits, setEdits] = useState<Record<string, LocalEdit>>({})

  const { data: strategies, isLoading, error, refetch } = useQuery({
    queryKey: ['strategyConfigs'],
    queryFn: fetchStrategyConfigs,
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const items = Object.entries(edits).map(([name, edit]) => ({
        name,
        ...edit,
      }))
      return batchUpdateStrategyConfig(items)
    },
    onSuccess: () => {
      message.success('策略配置已保存')
      setEdits({})
      queryClient.invalidateQueries({ queryKey: ['strategyConfigs'] })
    },
  })

  // 合并远程数据和本地编辑，得到当前展示状态
  const merged = useMemo(() => {
    if (!strategies) return []
    return strategies.map((s) => {
      const edit = edits[s.name]
      return {
        ...s,
        is_enabled: edit?.is_enabled ?? s.is_enabled,
        params: { ...s.params, ...(edit?.params ?? {}) },
      }
    })
  }, [strategies, edits])

  const hasEdits = Object.keys(edits).length > 0

  // 按分类分组
  const technicalStrategies = merged.filter((s) => s.category === 'technical')
  const fundamentalStrategies = merged.filter((s) => s.category === 'fundamental')

  const enabledCount = merged.filter((s) => s.is_enabled).length

  // 切换启用状态
  const toggleEnabled = (name: string, checked: boolean) => {
    setEdits((prev) => ({
      ...prev,
      [name]: { ...prev[name], is_enabled: checked },
    }))
  }

  // 修改参数
  const updateParam = (name: string, paramKey: string, value: number | null) => {
    if (value === null) return
    setEdits((prev) => {
      const existing = prev[name] ?? {}
      return {
        ...prev,
        [name]: {
          ...existing,
          params: { ...(existing.params ?? {}), [paramKey]: value },
        },
      }
    })
  }

  // 重置参数为默认值
  const resetParams = (name: string, defaultParams: Record<string, number>) => {
    setEdits((prev) => ({
      ...prev,
      [name]: { ...prev[name], params: { ...defaultParams } },
    }))
  }

  if (error) return <QueryErrorAlert error={error} refetch={refetch} />

  // 渲染策略参数编辑区
  const renderParams = (item: StrategyConfig & { params: Record<string, number> }) => {
    const keys = Object.keys(item.default_params)
    if (keys.length === 0) return <span style={{ color: '#999' }}>无可配置参数</span>
    return (
      <Space wrap>
        {keys.map((key) => (
          <span key={key}>
            {key}：
            <InputNumber
              size="small"
              value={item.params[key] ?? item.default_params[key]}
              step={typeof item.default_params[key] === 'number' && item.default_params[key] % 1 !== 0 ? 0.1 : 1}
              onChange={(v) => updateParam(item.name, key, v)}
              style={{ width: 90 }}
            />
          </span>
        ))}
        <Button
          size="small"
          icon={<UndoOutlined />}
          onClick={() => resetParams(item.name, item.default_params as Record<string, number>)}
        >
          重置
        </Button>
      </Space>
    )
  }

  // 渲染策略表格
  const renderTable = (items: typeof merged) => (
    <Table
      dataSource={items}
      rowKey="name"
      pagination={false}
      size="small"
      columns={[
        {
          title: '策略',
          dataIndex: 'display_name',
          width: 160,
        },
        {
          title: '说明',
          dataIndex: 'description',
          ellipsis: true,
        },
        {
          title: '启用',
          dataIndex: 'is_enabled',
          width: 80,
          align: 'center',
          render: (val: boolean, record) => (
            <Switch
              checked={val}
              onChange={(checked) => toggleEnabled(record.name, checked)}
            />
          ),
        },
      ]}
      expandable={{
        expandedRowRender: (record) => renderParams(record),
        rowExpandable: (record) => Object.keys(record.default_params).length > 0,
      }}
    />
  )

  const collapseItems = [
    {
      key: 'technical',
      label: (
        <Space>
          <span>技术面策略</span>
          <Badge
            count={technicalStrategies.filter((s) => s.is_enabled).length}
            style={{ backgroundColor: '#52c41a' }}
            showZero
          />
          <Tag>共 {technicalStrategies.length} 个</Tag>
        </Space>
      ),
      children: renderTable(technicalStrategies),
    },
    {
      key: 'fundamental',
      label: (
        <Space>
          <span>基本面策略</span>
          <Badge
            count={fundamentalStrategies.filter((s) => s.is_enabled).length}
            style={{ backgroundColor: '#52c41a' }}
            showZero
          />
          <Tag>共 {fundamentalStrategies.length} 个</Tag>
        </Space>
      ),
      children: renderTable(fundamentalStrategies),
    },
  ]

  return (
    <Card
      title={
        <Space>
          <span>策略配置</span>
          <Tag color="blue">已启用 {enabledCount} / {merged.length}</Tag>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<SaveOutlined />}
          disabled={!hasEdits}
          loading={saveMutation.isPending}
          onClick={() => saveMutation.mutate()}
        >
          保存配置
        </Button>
      }
      loading={isLoading}
    >
      <Collapse
        defaultActiveKey={['technical', 'fundamental']}
        items={collapseItems}
      />
    </Card>
  )
}
