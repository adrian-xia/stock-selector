import axios from 'axios'
import { message } from 'antd'

/** 统一 Axios 实例，baseURL 指向 /api/v1 */
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

// 响应拦截器：统一错误提示
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const msg =
      error.response?.data?.detail ??
      error.response?.data?.message ??
      error.message ??
      '请求失败'
    message.error(msg)
    return Promise.reject(error)
  },
)

export default apiClient
