import axios from 'axios'

const baseURL = import.meta.env.VITE_API_URL || '/api'
export const api = axios.create({ baseURL, withCredentials: true })
api.interceptors.response.use(r => r, error => {
  if (error.response?.status === 401) {
    if (!location.pathname.includes('/login')) location.href = '/login'
  }
  return Promise.reject(error)
})
