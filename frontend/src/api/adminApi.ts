import { User } from './authApi'
import { apiRequest } from './http'

export type AdminUser = User & {
  tokens_used_today: number
  daily_token_limit_per_user: number
}

export const adminApi = {
  listUsers: () => apiRequest<AdminUser[]>('/admin/users'),
  updateStatus: (userId: string, isActive: boolean) =>
    apiRequest<AdminUser>(`/admin/users/${encodeURIComponent(userId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    }),
  updateRole: (userId: string, role: User['role']) =>
    apiRequest<AdminUser>(`/admin/users/${encodeURIComponent(userId)}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
}
