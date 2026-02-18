import { Layout, Menu } from 'antd'
import { ExperimentOutlined, LineChartOutlined, ControlOutlined } from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'

const { Sider, Content } = Layout

const menuItems = [
  {
    key: '/workbench',
    icon: <ExperimentOutlined />,
    label: '选股工作台',
  },
  {
    key: '/backtest',
    icon: <LineChartOutlined />,
    label: '回测中心',
  },
  {
    key: '/optimization',
    icon: <ControlOutlined />,
    label: '参数优化',
  },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  // 根据当前路径确定选中的菜单项
  const selectedKey = location.pathname.startsWith('/optimization')
    ? '/optimization'
    : location.pathname.startsWith('/backtest')
    ? '/backtest'
    : '/workbench'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider breakpoint="lg" collapsedWidth={60}>
        <div style={{ height: 32, margin: 16, color: '#fff', fontWeight: 'bold', textAlign: 'center', fontSize: 16 }}>
          智能选股
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Content style={{ margin: 16 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
