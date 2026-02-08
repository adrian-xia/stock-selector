## ADDED Requirements

### Requirement: Vite React TypeScript 项目初始化
系统 SHALL 在 `web/` 目录下创建基于 Vite 6 的 React 18 + TypeScript 前端项目，使用 pnpm 管理依赖。

#### Scenario: 项目创建后可正常启动
- **WHEN** 在 `web/` 目录执行 `pnpm dev`
- **THEN** Vite 开发服务器在 `localhost:5173` 启动，浏览器可访问页面

#### Scenario: TypeScript 类型检查通过
- **WHEN** 执行 `pnpm tsc --noEmit`
- **THEN** 无类型错误

### Requirement: Ant Design 5 集成
系统 SHALL 集成 Ant Design 5 作为 UI 组件库，使用 CSS-in-JS 模式（无需额外 CSS 导入）。

#### Scenario: Ant Design 组件可正常渲染
- **WHEN** 页面中使用 Ant Design 的 Button、Table 等组件
- **THEN** 组件正确渲染，样式正常显示

### Requirement: 路由配置
系统 SHALL 使用 React Router v6 配置以下路由：`/`（重定向到 `/workbench`）、`/workbench`、`/backtest`、`/backtest/new`、`/backtest/:taskId`。

#### Scenario: 路由导航正常
- **WHEN** 用户访问 `/`
- **THEN** 自动重定向到 `/workbench`

#### Scenario: 未知路由处理
- **WHEN** 用户访问不存在的路径
- **THEN** 显示 404 页面或重定向到首页

### Requirement: 应用布局
系统 SHALL 提供统一的 AppLayout 组件，包含左侧导航栏（Ant Design Sider），导航项为「选股工作台」和「回测中心」。

#### Scenario: 导航栏高亮当前页面
- **WHEN** 用户在 `/workbench` 页面
- **THEN** 左侧导航栏「选股工作台」项高亮

### Requirement: Axios 实例配置
系统 SHALL 创建统一的 Axios 实例，配置 baseURL 为 `/api/v1`，并设置响应拦截器统一处理错误（弹出 Ant Design message 提示）。

#### Scenario: API 请求自动添加前缀
- **WHEN** 调用 `api.get("/strategy/list")`
- **THEN** 实际请求发送到 `/api/v1/strategy/list`

#### Scenario: API 错误统一提示
- **WHEN** 后端返回 4xx/5xx 错误
- **THEN** 页面顶部显示 Ant Design message 错误提示，包含错误信息

### Requirement: Vite 代理配置
系统 SHALL 配置 Vite 开发服务器将 `/api` 请求代理到后端 `http://localhost:8000`。

#### Scenario: 开发环境 API 代理
- **WHEN** 前端发送 `/api/v1/strategy/list` 请求
- **THEN** Vite 将请求转发到 `http://localhost:8000/api/v1/strategy/list`

### Requirement: React Query 配置
系统 SHALL 配置 TanStack React Query 的 QueryClientProvider，设置默认 staleTime 和 retry 策略。

#### Scenario: React Query 全局可用
- **WHEN** 任意组件中调用 `useQuery`
- **THEN** 正常工作，无需额外 Provider 配置
