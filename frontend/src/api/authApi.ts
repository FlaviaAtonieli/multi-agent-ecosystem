import { API_URL, apiRequest } from './http'

export type User = {
  id: string
  name: string
  email: string
  role: 'USER' | 'TECHNICIAN' | 'REVIEWER' | 'ADMIN'
  is_active: boolean
  avatar_url: string | null
  created_at: string
  onboarding_completed_at: string | null
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

// Navegacao de pagina inteira, nao uma chamada fetch: o backend precisa
// redirecionar o navegador ate o GitHub (e o GitHub de volta) pra completar
// o fluxo OAuth, o que uma requisicao XHR/fetch nao consegue fazer.
export const githubLoginUrl = `${API_URL}/auth/github/login`

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
  completeOnboarding: () => apiRequest<User>('/auth/onboarding/complete', { method: 'POST' }),
}
