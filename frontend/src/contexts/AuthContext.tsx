import React, { createContext, useContext, useState, ReactNode } from 'react'

interface User {
  id: number
  username: string
  full_name: string
  role: string
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (user: User, token: string) => void
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const saved = localStorage.getItem('auth_user')
    return saved ? JSON.parse(saved) : null
  })
  const [token, setToken] = useState<string | null>(() =>
    localStorage.getItem('auth_token')
  )

  const login = (u: User, t: string) => {
    setUser(u)
    setToken(t)
    localStorage.setItem('auth_user', JSON.stringify(u))
    localStorage.setItem('auth_token', t)
  }

  const logout = () => {
    setUser(null)
    setToken(null)
    localStorage.removeItem('auth_user')
    localStorage.removeItem('auth_token')
    localStorage.removeItem('active_brand_id')
  }

  return (
    <AuthContext.Provider value={{ user, token, login, logout, isAuthenticated: !!token }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be inside AuthProvider')
  return ctx
}
