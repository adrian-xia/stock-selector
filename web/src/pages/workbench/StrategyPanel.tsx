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

  // 按分类分组
  const grouped: Record<string, StrategyMeta[]> = {}
  for (const s of strategies) {
    const cat = s.category === 'technical' ? '技术面' : '基本面'
    if (!grouped[cat]) grouped[cat] = []
    grouped[cat].push(s)
  }

  return (
    <div>
      {Object.entries(grouped).map(([category, items]) => (
        <Card
          key={category}
          title={<Tag color={category === '技术面' ? 'blue' : 'green'}>{category}</Tag>}
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
