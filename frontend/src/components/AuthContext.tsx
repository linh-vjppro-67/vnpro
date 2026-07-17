import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { User } from '../types'
import { api } from '../lib/api'

type AuthValue = { user: User | null; login: (email: string, password: string) => Promise<void>; logout: () => void }
const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: {children: ReactNode}) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem('pro_user'); return raw ? JSON.parse(raw) : null
  })
  const value = useMemo<AuthValue>(() => ({
    user,
    login: async (email, password) => {
      const { data } = await api.post('/auth/login', { email, password })
      localStorage.setItem('pro_token', data.access_token)
      localStorage.setItem('pro_user', JSON.stringify(data.user))
      setUser(data.user)
    },
    logout: () => { localStorage.removeItem('pro_token'); localStorage.removeItem('pro_user'); setUser(null) }
  }), [user])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider missing')
  return value
}
