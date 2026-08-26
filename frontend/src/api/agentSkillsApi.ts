import { apiRequest } from './http'

export type AgentSkillDomain =
  | 'codigo_legado'
  | 'regras_negocio'
  | 'arquitetura_software'
  | 'seguranca_informacao'

export type AgentSkill = {
  id: string
  name: string
  version: string
  domain: AgentSkillDomain
  status: string
  enabled: boolean
  author_origin: string
  objective: string
  input_contract_ref: string
  output_contract_ref: string
  uses_external_services: boolean
  validated_at: string | null
  created_at: string
  updated_at: string
}

export type ConfidenceLevel = 'ALTO' | 'MEDIO' | 'BAIXO'

export type SkillToolResult = {
  trace_id: string
  agente_emissor: {
    nome: string
    versao_prompt: string | null
    dominio: AgentSkillDomain
  }
  analise_estruturada: {
    resumo_executivo: string
    descobertas_tecnicas: Array<{
      item_identificado: string
      descricao_detalhada: string
      trecho_referenciado: string | null
    }>
    impactos_mapeados: string[]
  }
  governanca: {
    nivel_confianca: ConfidenceLevel
    justificativa_confianca: string
    referencias_catalogo: string[]
  }
}

export type QualityGateVerdict = {
  approved: boolean
  requires_human_review: boolean
  reasons: string[]
}

export type ConsolidatedResponse = {
  id: string
  trace_id: string
  technical_synthesis: string
  recommendations: string[]
  risks: string[]
  limitations: string[]
  participating_agents: string[]
  overall_confidence_level: ConfidenceLevel
  quality_gate_approved: boolean
  requires_human_review: boolean
  invocation_ids: string[]
  created_at: string
}

export type OrchestrationExecutionResult = {
  results: SkillToolResult[]
  verdict: QualityGateVerdict
  invocations_count: number
  consolidated_response: ConsolidatedResponse
}

export const agentSkillsApi = {
  listSkills: (onlyActive = false) =>
    apiRequest<AgentSkill[]>(`/agent-skills?only_active=${onlyActive}`),
  importSkill: (manifestMarkdown: string) =>
    apiRequest<AgentSkill>('/agent-skills/import', {
      method: 'POST',
      body: JSON.stringify({ manifest_markdown: manifestMarkdown }),
    }),
  enableSkill: (id: string) =>
    apiRequest<AgentSkill>(`/agent-skills/${encodeURIComponent(id)}/enable`, { method: 'PATCH' }),
  disableSkill: (id: string) =>
    apiRequest<AgentSkill>(`/agent-skills/${encodeURIComponent(id)}/disable`, { method: 'PATCH' }),
  execute: (requestId: string, model: string | null) =>
    apiRequest<OrchestrationExecutionResult>(
      `/agent-skills/requests/${encodeURIComponent(requestId)}/execute`,
      {
        method: 'POST',
        body: JSON.stringify({ model }),
      },
    ),
}
