import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import ErrorBoundary from './components/common/ErrorBoundary'
import PageLoading from './components/common/PageLoading'

/* 路由级懒加载 */
const WorkbenchPage = lazy(() => import('./pages/workbench/WorkbenchPage'))
const BacktestListPage = lazy(() => import('./pages/backtest/BacktestListPage'))
const BacktestNewPage = lazy(() => import('./pages/backtest/BacktestNewPage'))
const BacktestDetailPage = lazy(() => import('./pages/backtest/BacktestDetailPage'))
const OptimizationPage = lazy(() => import('./pages/optimization'))
const NewsPage = lazy(() => import('./pages/news'))
const MonitorPage = lazy(() => import('./pages/monitor'))
const StrategyConfigPage = lazy(() => import('./pages/strategy-config'))

/** 路由切换时重置 ErrorBoundary */
function ErrorBoundaryResetter({ children }: { children: React.ReactNode }) {
  const location = useLocation()
  // key 绑定 pathname，路由切换时 ErrorBoundary 自动重置
  return <ErrorBoundary key={location.pathname}>{children}</ErrorBoundary>
}

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/workbench" replace />} />
        <Route path="/workbench" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><WorkbenchPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/backtest" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><BacktestListPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/backtest/new" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><BacktestNewPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/backtest/:taskId" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><BacktestDetailPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/optimization" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><OptimizationPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/news" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><NewsPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/monitor" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><MonitorPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
        <Route path="/strategy-config" element={
          <ErrorBoundaryResetter>
            <Suspense fallback={<PageLoading />}><StrategyConfigPage /></Suspense>
          </ErrorBoundaryResetter>
        } />
      </Route>
    </Routes>
  )
}

export default App
