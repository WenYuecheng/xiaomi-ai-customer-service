import axios from 'axios'

const TOKEN_KEY = 'xmcs_access_token'

export const api = axios.create({ baseURL: '/api/v1', timeout: 30_000 })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error?.message ?? '服务暂时不可用，请稍后重试'
    return Promise.reject(new Error(message))
  },
)

export { TOKEN_KEY }

