import axios from 'axios'

const request = axios.create({
  baseURL: 'http://127.0.0.1:8000', // ✅ 强制打到 FastAPI
  timeout: 30000,
})

// ✅ 请求拦截：自动带上 token
request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers = config.headers || {}
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (err) => Promise.reject(err)
)

// ✅ 统一解包：保持你现有逻辑不变
request.interceptors.response.use(
  (res) => {
    // 有些情况下会拿到 Vite 返回的 HTML（典型：baseURL/代理错）
    if (typeof res.data === 'string' && res.data.includes('<!DOCTYPE html>')) {
      return Promise.reject(new Error('API 请求打到了前端服务器（返回了 HTML），请检查 baseURL/代理配置'))
    }
    return res.data
  },
  (err) => {
    // ✅ 可选：如果后端返回 401，自动回到登录页
    if (err.response && err.response.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('username')
      localStorage.removeItem('role')

      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)

export default request