import { apiRequest } from './http'
import { OrchestrationEvent, TechnicalRequest } from './orchestrationApi'

export type DashboardSummary = {
  active_sessions: number
  registered_agent_skills: number
  orchestration_executions: number
  running_orchestrations: number
  awaiting_context: number
  completed_today: number
  success_rate: number
  average_duration_seconds: number
  total_users: number | null
  recent_security_events: Array<{
    event_type: string
    created_at: string
  }>
  recent_requests: TechnicalRequest[]
  recent_orchestration_events: OrchestrationEvent[]
}

export const dashboardApi = {
  summary: () => apiRequest<DashboardSummary>('/dashboard/summary'),
}
