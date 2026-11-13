import { API_URL, apiRequest } from './http'
import { ConsolidatedResponse, FollowUpExchange, SkillToolResult } from './agentSkillsApi'

export type RequestStatus =
  | 'RECEIVED'
  | 'AWAITING_CONTEXT'
  | 'QUALIFIED'
  | 'PLANNING'
  | 'RUNNING'
  | 'VALIDATING'
  | 'COMPLETED'
  | 'REJECTED'
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
  requested_domains: string[]
  clan_id: string | null
  status: RequestStatus
  created_at: string
  updated_at: string
  consolidated_response: ConsolidatedResponse | null
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

export type FeedbackReason = 'INCORRETA' | 'INCOMPLETA' | 'FORA_DO_ASSUNTO' | 'SEM_EVIDENCIA'

export type AgentResponseFeedback = {
  useful: boolean
  reason: FeedbackReason | null
  comment: string | null
  updated_at: string
}

export type AgentResponseFeedbackInput = {
  useful: boolean
  reason?: FeedbackReason | null
  comment?: string | null
}

export type AgentSkillInvocationResult = {
  id: string
  agent_skill_name: string
  status: string
  confidence_level: string | null
  result: SkillToolResult | null
  created_at: string
  feedback: AgentResponseFeedback | null
}

export type CreateTechnicalRequestInput = {
  title: string
  problem: string
  objective: string
  context: string | null
  restrictions: string[]
  requested_domains: string[]
  clan_id: string
}

export type RequestAttachment = {
  id: string
  filename: string
  content_type: string | null
  size_bytes: number
  created_at: string
}

export type SkillArtifact = {
  id: string
  filename: string
  size_bytes: number
  agent_skill_name: string
  domain: string
  created_at: string
}

export type SkillArtifactContent = SkillArtifact & { content: string }

function artifactsPath(traceId: string) {
  return `/orchestrations/${encodeURIComponent(traceId)}/artifacts`
}

// Downloads são links diretos: usam o cookie de sessão e o navegador salva o arquivo.
export const artifactDownloadUrl = (traceId: string, artifactId: string) =>
  `${API_URL}${artifactsPath(traceId)}/${encodeURIComponent(artifactId)}/download`

export const artifactsZipUrl = (traceId: string) => `${API_URL}${artifactsPath(traceId)}.zip`

export const orchestrationApi = {
  listArtifacts: (traceId: string) => apiRequest<SkillArtifact[]>(artifactsPath(traceId)),
  getArtifact: (traceId: string, artifactId: string) =>
    apiRequest<SkillArtifactContent>(`${artifactsPath(traceId)}/${encodeURIComponent(artifactId)}`),
  listRequests: () => apiRequest<TechnicalRequest[]>('/requests'),
  createRequest: (input: CreateTechnicalRequestInput) =>
    apiRequest<TechnicalRequest>('/requests', {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  listAttachments: (requestId: string) =>
    apiRequest<RequestAttachment[]>(`/requests/${encodeURIComponent(requestId)}/attachments`),
  uploadAttachment: (requestId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiRequest<RequestAttachment>(`/requests/${encodeURIComponent(requestId)}/attachments`, {
      method: 'POST',
      body: formData,
    })
  },
  deleteAttachment: (requestId: string, attachmentId: string) =>
    apiRequest<void>(
      `/requests/${encodeURIComponent(requestId)}/attachments/${encodeURIComponent(attachmentId)}`,
      { method: 'DELETE' },
    ),
  getOrchestration: (traceId: string) =>
    apiRequest<OrchestrationDetail>(`/orchestrations/${encodeURIComponent(traceId)}`),
  getSkillResults: (traceId: string) =>
    apiRequest<AgentSkillInvocationResult[]>(`/orchestrations/${encodeURIComponent(traceId)}/skill-results`),
  rateSkillResult: (traceId: string, invocationId: string, input: AgentResponseFeedbackInput) =>
    apiRequest<AgentResponseFeedback>(
      `/orchestrations/${encodeURIComponent(traceId)}/skill-results/${encodeURIComponent(invocationId)}/feedback`,
      { method: 'PUT', body: JSON.stringify(input) },
    ),
  removeSkillResultRating: (traceId: string, invocationId: string) =>
    apiRequest<void>(
      `/orchestrations/${encodeURIComponent(traceId)}/skill-results/${encodeURIComponent(invocationId)}/feedback`,
      { method: 'DELETE' },
    ),
  getFollowUps: (traceId: string) =>
    apiRequest<FollowUpExchange[]>(`/orchestrations/${encodeURIComponent(traceId)}/follow-ups`),
  addContext: (requestId: string, context: string) =>
    apiRequest<TechnicalRequest>(`/requests/${encodeURIComponent(requestId)}/context`, {
      method: 'POST',
      body: JSON.stringify({ context }),
    }),
  review: (requestId: string, decision: 'approve' | 'reject', notes: string | null) =>
    apiRequest<TechnicalRequest>(`/requests/${encodeURIComponent(requestId)}/review`, {
      method: 'POST',
      body: JSON.stringify({ decision, notes }),
    }),
}
