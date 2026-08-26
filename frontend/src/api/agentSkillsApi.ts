import { apiRequest } from './http'

export type AgentSkillDomain = 'codigo_legado' | 'regras_negocio' | 'arquitetura_software'

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
}
