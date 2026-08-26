import { apiRequest } from './http'

export type RequestStatus =
  | 'RECEIVED'
  | 'AWAITING_CONTEXT'
  | 'QUALIFIED'
  | 'PLANNING'
  | 'RUNNING'
  | 'VALIDATING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'

export type TechnicalRequest = {
  id: string
  trace_id: string
  title: string
  problem: string
  objective: string
  context: string | null
  restrictions: string[]
  status: RequestStatus
  created_at: string
  updated_at: string
}

export type OrchestrationRun = {
  id: string
  status: RequestStatus
  current_stage: string
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}

export type OrchestrationEvent = {
  id: string
  sequence_number: number
  event_type: string
  actor: string
  title: string
  message: string
  payload: Record<string, unknown>
  created_at: string
}

export type OrchestrationDetail = {
  technical_request: TechnicalRequest
  run: OrchestrationRun
  events: OrchestrationEvent[]
}

export type CreateTechnicalRequestInput = {
  title: string
  problem: string
  objective: string
  context: string | null
  restrictions: string[]
}

export const orchestrationApi = {
  listRequests: () => apiRequest<TechnicalRequest[]>('/requests'),
  createRequest: (input: CreateTechnicalRequestInput) =>
    apiRequest<TechnicalRequest>('/requests', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  getOrchestration: (traceId: string) =>
    apiRequest<OrchestrationDetail>(`/orchestrations/${encodeURIComponent(traceId)}`),
  addContext: (requestId: string, context: string) =>
    apiRequest<TechnicalRequest>(`/requests/${encodeURIComponent(requestId)}/context`, {
      method: 'POST',
      body: JSON.stringify({ context }),
    }),
}
