import { apiRequest } from './http'

export type User = {
  id: string
  name: string
  email: string
  role: 'USER' | 'TECHNICIAN' | 'ADMIN'
  is_active: boolean
  created_at: string
}

export type AuthResponse = {
  user: User
  session_expires_at: string
}

export type RegisterInput = {
  name: string
  email: string
  password: string
}

export type LoginInput = {
  email: string
  password: string
}

export const authApi = {
  me: () => apiRequest<User>('/auth/me'),
  login: (input: LoginInput) =>
    apiRequest<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  register: (input: RegisterInput) =>
    apiRequest<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  renew: () => apiRequest<AuthResponse>('/auth/renew', { method: 'POST' }),
  logout: () => apiRequest<void>('/auth/logout', { method: 'POST' }),
  logoutAll: () => apiRequest<void>('/auth/logout-all', { method: 'POST' }),
}
