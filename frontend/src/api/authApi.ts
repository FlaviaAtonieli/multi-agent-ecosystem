import { API_URL, apiRequest } from './http'

export type User = {
  id: string
  name: string
  email: string
  is_active: boolean
  avatar_url: string | null
  created_at: string
  onboarding_completed_at: string | null
  has_password: boolean
  oauth_provider: 'github' | 'google' | null
}

export type AuthResponse = {
  user: User
  session_expires_at: string
}

// Login em dispositivo/navegador novo: a sessão só é criada depois de
// confirmar o código enviado ao e-mail (POST /auth/login/verify).
export type LoginChallenge = {
  verification_required: true
  email_hint: string
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
// redirecionar o navegador ate o GitHub/Google (e de volta) pra completar
// o fluxo OAuth, o que uma requisicao XHR/fetch nao consegue fazer.
export const githubLoginUrl = `${API_URL}/auth/github/login`
export const googleLoginUrl = `${API_URL}/auth/google/login`

export const authApi = {
  me: () => apiRequest<User>('/auth/me'),
  login: (input: LoginInput) =>
    apiRequest<AuthResponse | LoginChallenge>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  loginChallenge: () => apiRequest<LoginChallenge>('/auth/login/challenge'),
  verifyLoginCode: (code: string) =>
    apiRequest<AuthResponse>('/auth/login/verify', { method: 'POST', body: JSON.stringify({ code }) }),
  resendLoginCode: () => apiRequest<LoginChallenge>('/auth/login/resend', { method: 'POST' }),
  forgotPassword: (email: string) =>
    apiRequest<{ message: string }>('/auth/password/forgot', { method: 'POST', body: JSON.stringify({ email }) }),
  resetPassword: (token: string, newPassword: string) =>
    apiRequest<void>('/auth/password/reset', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
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
  updateName: (name: string) =>
    apiRequest<User>('/auth/me', { method: 'PATCH', body: JSON.stringify({ name }) }),
  changePassword: (currentPassword: string, newPassword: string) =>
    apiRequest<User>('/auth/me/password', {
      method: 'POST',
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),
  deleteAccount: () => apiRequest<void>('/auth/me', { method: 'DELETE' }),
}
