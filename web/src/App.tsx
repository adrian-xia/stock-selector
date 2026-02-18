import { Navigate, Route, Routes } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import WorkbenchPage from './pages/workbench/WorkbenchPage'
import BacktestListPage from './pages/backtest/BacktestListPage'
import BacktestNewPage from './pages/backtest/BacktestNewPage'
import BacktestDetailPage from './pages/backtest/BacktestDetailPage'
import OptimizationPage from './pages/optimization'

function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<Navigate to="/workbench" replace />} />
        <Route path="/workbench" element={<WorkbenchPage />} />
        <Route path="/backtest" element={<BacktestListPage />} />
        <Route path="/backtest/new" element={<BacktestNewPage />} />
        <Route path="/backtest/:taskId" element={<BacktestDetailPage />} />
        <Route path="/optimization" element={<OptimizationPage />} />
      </Route>
    </Routes>
  )
}

export default App
