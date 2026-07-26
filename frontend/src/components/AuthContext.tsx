import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import type { User } from '../types'
import { api } from '../lib/api'

type AuthValue = { user: User | null; loading: boolean; login: (email: string, password: string) => Promise<void>; logout: () => Promise<void> }
const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: {children: ReactNode}) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    api.get('/auth/me').then(r => setUser(r.data)).catch(() => setUser(null)).finally(() => setLoading(false))
  }, [])
  const value = useMemo<AuthValue>(() => ({
    user, loading,
    login: async (email, password) => {
      const { data } = await api.post('/auth/login', { email, password })
      setUser(data.user)
    },
    logout: async () => {
      try { await api.post('/auth/logout') } finally { setUser(null) }
    },
  }), [user, loading])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider missing')
  return value
}
