import { User } from './authApi'
import { apiRequest } from './http'

export const adminApi = {
  listUsers: () => apiRequest<User[]>('/admin/users'),
  updateStatus: (userId: string, isActive: boolean) =>
    apiRequest<User>(`/admin/users/${encodeURIComponent(userId)}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ is_active: isActive }),
    }),
  updateRole: (userId: string, role: User['role']) =>
    apiRequest<User>(`/admin/users/${encodeURIComponent(userId)}/role`, {
      method: 'PATCH',
      body: JSON.stringify({ role }),
    }),
}
