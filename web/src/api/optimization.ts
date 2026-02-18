import apiClient from './client'
import type {
  OptimizationRunRequest,
  OptimizationRunResponse,
  OptimizationResultResponse,
  OptimizationListResponse,
  ParamSpaceResponse,
} from '../types/optimization'

/** 提交优化任务 */
export async function runOptimization(req: OptimizationRunRequest) {
  const { data } = await apiClient.post<OptimizationRunResponse>('/optimization/run', req)
  return data
}

/** 查询优化结果 */
export async function fetchOptimizationResult(taskId: number) {
  const { data } = await apiClient.get<OptimizationResultResponse>(`/optimization/result/${taskId}`)
  return data
}

/** 查询优化任务列表 */
export async function fetchOptimizationList(page = 1, pageSize = 20) {
  const { data } = await apiClient.get<OptimizationListResponse>('/optimization/list', {
    params: { page, page_size: pageSize },
  })
  return data
}

/** 查询策略参数空间 */
export async function fetchParamSpace(strategyName: string) {
  const { data } = await apiClient.get<ParamSpaceResponse>(`/optimization/param-space/${strategyName}`)
  return data
}
