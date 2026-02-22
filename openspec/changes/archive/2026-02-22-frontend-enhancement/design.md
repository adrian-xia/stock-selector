## Context

前端基于 React 19 + Ant Design 6 + ECharts 6 + React Query 5 + Zustand 5 构建，共 5 个页面（workbench、backtest、optimization、news、monitor）。当前存在三类问题：

1. **数据获取不统一**：workbench 和 backtest 使用 React Query，其余 3 个页面使用原生 useState/useEffect
2. **错误处理缺失**：无全局 ErrorBoundary，MonitorPage 完全静默失败，多数页面无错误 UI
3. **无性能优化**：路由同步导入无懒加载，无代码分割，ECharts 全量引入

约束：纯前端变更，不涉及后端 API 修改。复用已有依赖（React 19 Suspense、Zustand 5 等）。

## Goals / Non-Goals

**Goals:**
- 统一 5 个页面的数据获取模式为 React Query
- 提供全局错误边界和统一加载/错误 UI 组件
- 路由级懒加载 + Vite chunk 分割，减小首屏包体积
- StockDetail 集成 K 线图（复用已有 `api/data.ts`）
- ECharts 公共主题和配置复用
- MonitorPage 拆分为可维护的子组件
- 关键页面响应式布局适配

**Non-Goals:**
- 不新增后端 API
- 不引入新的 UI 框架或图表库
- 不做 SSR/SSG
- 不做国际化 i18n
- 不做完整的移动端 App 适配（仅基础响应式）

## Decisions

### D1: React Query 统一数据获取

**选择：** 将 news、optimization、monitor 三个页面迁移到 React Query

**理由：** React Query 已在 workbench/backtest 中使用，提供自动缓存、重试、loading/error 状态管理。统一后消除手动 state 管理的样板代码，错误处理自动一致。

**替代方案：** 保持现状各页面独立管理 → 拒绝，维护成本高且行为不一致。

### D2: ErrorBoundary + Suspense 分层策略

**选择：** 路由级 ErrorBoundary（捕获页面崩溃）+ 页面内 React Query error 状态（业务错误）

**理由：** React 19 原生支持 Suspense，配合 React.lazy 实现路由懒加载。ErrorBoundary 作为兜底，React Query 的 error 状态处理 API 错误。两层互补。

**实现：** 创建 `components/common/ErrorBoundary.tsx` 和 `components/common/PageLoading.tsx`。

### D3: 路由懒加载 + Vite chunk 分割

**选择：** React.lazy 按页面分割 + vite.config.ts 配置 manualChunks

**分割策略：**
- `vendor-react`: react + react-dom + react-router-dom
- `vendor-antd`: antd + @ant-design/icons
- `vendor-echarts`: echarts + echarts-for-react
- 每个页面独立 chunk

**理由：** 5 个页面用户通常只访问 1-2 个，懒加载避免加载未使用页面代码。ECharts 体积大，单独分割。

### D4: K 线图组件设计

**选择：** 基于 ECharts candlestick 图表，集成到 StockDetail 组件

**功能：** K 线主图 + 成交量副图 + MA5/MA10/MA20 均线叠加，支持日期范围选择（dataZoom）

**数据源：** 复用 `api/data.ts` 的 `fetchKline` 函数，通过 React Query 管理请求。

### D5: ECharts 主题和配置复用

**选择：** 创建 `utils/chartTheme.ts` 统一颜色、tooltip、grid 等公共配置

**理由：** 当前两处 ECharts 使用（EquityCurve + 情感趋势图）配置完全内联无复用。K 线图是第三处使用，需要统一风格。

## Risks / Trade-offs

- **[React Query 迁移可能改变请求时序]** → 逐页面迁移，每页面迁移后验证行为一致
- **[懒加载增加首次页面切换延迟]** → PageLoading 组件提供视觉反馈，chunk 预加载（prefetch）
- **[MonitorPage 拆分可能引入 props drilling]** → 组件间通过 React Query hooks 共享数据，避免深层传递
- **[K 线图数据量大时性能问题]** → ECharts dataZoom 限制可视范围，默认加载最近 120 个交易日

## Open Questions

无。
