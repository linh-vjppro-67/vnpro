import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || '/api'
export const api = axios.create({ baseURL })
api.interceptors.request.use(config => {
  const token = localStorage.getItem('pro_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
api.interceptors.response.use(r => r, error => {
  if (error.response?.status === 401) {
    localStorage.removeItem('pro_token')
    localStorage.removeItem('pro_user')
    if (!location.pathname.includes('/login')) location.href = '/login'
  }
  return Promise.reject(error)
})
