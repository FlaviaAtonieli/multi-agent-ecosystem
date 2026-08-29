import { apiRequest } from './http'

export type LLMStatus = {
  enabled: boolean
  provider: string
  model: string
  configured: boolean
  allowed_models: string[]
  max_input_chars: number
  max_output_tokens: number
  requests_per_hour_technician: number
  store_provider_response: boolean
  store_result_content: boolean
  daily_token_limit_per_user: number
  tokens_used_today: number
}

export const llmApi = {
  status: () => apiRequest<LLMStatus>('/llm/status'),
}
