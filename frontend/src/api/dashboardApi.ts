import { apiRequest } from './http'

export type DashboardSummary = {
  active_sessions: number
  registered_agent_skills: number
  orchestration_executions: number
  total_users: number | null
  recent_security_events: Array<{
    event_type: string
    created_at: string
  }>
}

export const dashboardApi = {
  summary: () => apiRequest<DashboardSummary>('/dashboard/summary'),
}
