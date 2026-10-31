import axios from 'axios'

export const api = axios.create({ baseURL: import.meta.env.VITE_API_BASE || '/api/admin' })

api.interceptors.request.use((cfg) => {
  const t = localStorage.getItem('yolda-token')
  if (t) cfg.headers.Authorization = `Bearer ${t}`
  return cfg
})
api.interceptors.response.use(
  (r) => r,
  (e) => {
    if (e.response?.status === 401 && !location.pathname.startsWith('/login')) {
      localStorage.removeItem('yolda-token')
      location.href = '/login'
    }
    return Promise.reject(e)
  },
)

export const errMsg = (e: any): string => {
  const d = e?.response?.data?.detail
  if (typeof d === 'string') return d
  if (Array.isArray(d)) return d.map((x) => x.msg).join('; ')
  return e?.message || 'Xatolik yuz berdi'
}

export const get = <T = any>(url: string, params?: any) => api.get<T>(url, { params }).then((r) => r.data)
export const post = <T = any>(url: string, body?: any) => api.post<T>(url, body).then((r) => r.data)
export const del = <T = any>(url: string) => api.delete<T>(url).then((r) => r.data)
export const patch = <T = any>(url: string, body?: any) => api.patch<T>(url, body).then((r) => r.data)
