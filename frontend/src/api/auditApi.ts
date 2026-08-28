import { apiRequest } from './http'

export type AuditEvent = {
  id: string
  event_type: string
  actor: string
  title: string
  message: string
  created_at: string
  request_id: string
  request_title: string
  request_trace_id: string
}

export type AuditStats = {
  events_today: number
  automated_decisions_today: number
  manual_interventions_today: number
  compliance_alerts_today: number
}

export type AuditEventPage = {
  stats: AuditStats
  items: AuditEvent[]
  total: number
}

export type AuditEventsQuery = {
  days?: number
  actor?: string
  search?: string
  limit?: number
  offset?: number
}

export const auditApi = {
  listEvents: (query: AuditEventsQuery = {}) => {
    const params = new URLSearchParams()
    if (query.days) params.set('days', String(query.days))
    if (query.actor) params.set('actor', query.actor)
    if (query.search) params.set('search', query.search)
    if (query.limit) params.set('limit', String(query.limit))
    if (query.offset) params.set('offset', String(query.offset))
    const suffix = params.toString() ? `?${params.toString()}` : ''
    return apiRequest<AuditEventPage>(`/audit/events${suffix}`)
  },
}
