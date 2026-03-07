import { Card, Checkbox, List, Spin, Tag, Typography, Alert, Button } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { fetchStrategyList } from '../../api/strategy'
import type { StrategyMeta } from '../../types'

const { Text } = Typography

interface Props {
  selected: string[]
  onToggle: (name: string, meta: StrategyMeta) => void
}

export default function StrategyPanel({ selected, onToggle }: Props) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['strategyList'],
    queryFn: () => fetchStrategyList(),
  })

  if (isLoading) return <Spin tip="加载策略列表..." />
  if (error) {
    return (
      <Alert
        type="error"
        message="策略列表加载失败"
        action={<Button size="small" onClick={() => refetch()}>重试</Button>}
      />
    )
  }

  const strategies = data?.strategies ?? []
  const categoryLabelMap: Record<string, string> = {
    aggressive: '进攻组',
    trend: '趋势组',
    bottom: '底部组',
  }
  const categoryColorMap: Record<string, string> = {
    aggressive: 'red',
    trend: 'blue',
    bottom: 'green',
  }

  // 按分类分组
  const grouped: Record<string, StrategyMeta[]> = {}
  for (const s of strategies) {
    const cat = s.category
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(s)
  }

  return (
    <div>
      {Object.entries(grouped).map(([category, items]) => (
        <Card
          key={category}
          title={<Tag color={categoryColorMap[category] ?? 'default'}>{categoryLabelMap[category] ?? category}</Tag>}
          size="small"
          style={{ marginBottom: 12 }}
        >
          <List
            size="small"
            dataSource={items}
            renderItem={(item) => (
              <List.Item
                style={{ cursor: 'pointer', padding: '6px 0' }}
                onClick={() => onToggle(item.name, item)}
              >
                <Checkbox checked={selected.includes(item.name)} />
                <span style={{ marginLeft: 8 }}>
                  <Text strong>{item.display_name}</Text>
                  <Tag style={{ marginLeft: 8 }}>{item.ai_rating.toFixed(2)}</Tag>
                  <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                    {item.description}
                  </Text>
                </span>
              </List.Item>
            )}
          />
        </Card>
      ))}
    </div>
  )
}
