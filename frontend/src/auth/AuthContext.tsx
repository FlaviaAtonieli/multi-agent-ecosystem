import { createContext, ReactNode, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { authApi, LoginInput, RegisterInput, User } from '../api/authApi'
import { ApiError } from '../api/http'


type AuthContextValue = {
  user: User | null
  loading: boolean
  login: (input: LoginInput) => Promise<void>
  register: (input: RegisterInput) => Promise<void>
  logout: () => Promise<void>
  logoutAll: () => Promise<void>
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    try {
      setUser(await authApi.me())
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        setUser(null)
        return
      }
      throw error
    }
  }, [])

  useEffect(() => {
    refreshUser()
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [refreshUser])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      login: async (input) => {
        const result = await authApi.login(input)
        setUser(result.user)
      },
      register: async (input) => {
        const result = await authApi.register(input)
        setUser(result.user)
      },
      logout: async () => {
        try {
          await authApi.logout()
        } finally {
          setUser(null)
        }
      },
      logoutAll: async () => {
        try {
          await authApi.logoutAll()
        } finally {
          setUser(null)
        }
      },
      refreshUser,
    }),
    [loading, refreshUser, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth deve ser utilizado dentro de AuthProvider.')
  return context
}
