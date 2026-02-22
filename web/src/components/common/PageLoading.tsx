import { Spin } from 'antd'

/**
 * 页面级加载占位组件。
 * 用于 React.lazy + Suspense 的 fallback。
 */
export default function PageLoading() {
  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '60vh' }}>
      <Spin size="large" tip="加载中..." />
    </div>
  )
}
