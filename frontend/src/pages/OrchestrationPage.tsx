import { FormEvent, useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AgentSkillDomain, agentSkillsApi, FollowUpExchange, OrchestrationExecutionResult } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'
import { llmApi } from '../api/llmApi'
import { AgentSkillInvocationResult, OrchestrationDetail, orchestrationApi } from '../api/orchestrationApi'
import { ExecutionResultPanel } from '../components/orchestration/ExecutionResultPanel'
import { FollowUpExchangeCard } from '../components/orchestration/FollowUpExchangeCard'
import { FollowUpForm } from '../components/orchestration/FollowUpForm'
import { OrchestrationThinkingAnimation } from '../components/orchestration/OrchestrationThinkingAnimation'
import { StatusBadge } from '../components/orchestration/StatusBadge'
import { TokenUsageMeter } from '../components/orchestration/TokenUsageMeter'

export function OrchestrationPage() {
  const { traceId = '' } = useParams()
  const [detail, setDetail] = useState<OrchestrationDetail | null>(null)
  const [pastSkillResults, setPastSkillResults] = useState<AgentSkillInvocationResult[]>([])
  const [followUps, setFollowUps] = useState<FollowUpExchange[]>([])
  const [context, setContext] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [allowedModels, setAllowedModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [tokenUsage, setTokenUsage] = useState<{ used: number; limit: number } | null>(null)
  const [executing, setExecuting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [execution, setExecution] = useState<OrchestrationExecutionResult | null>(null)
  const [successMessage, setSuccessMessage] = useState('')
  const [askingFollowUp, setAskingFollowUp] = useState(false)
  const [followUpError, setFollowUpError] = useState('')
  const [activeSkillDomains, setActiveSkillDomains] = useState<AgentSkillDomain[]>([])

  const load = useCallback(async () => {
    try {
      const orchestration = await orchestrationApi.getOrchestration(traceId)
      setDetail(orchestration)
      setError('')
      if (orchestration.technical_request.consolidated_response) {
        orchestrationApi
          .getSkillResults(traceId)
          .then(setPastSkillResults)
          .catch(() => setPastSkillResults([]))
        orchestrationApi
          .getFollowUps(traceId)
          .then(setFollowUps)
          .catch(() => setFollowUps([]))
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar a orquestração.')
    }
  }, [traceId])

  const participatingDomains = useMemo(() => {
    const domains: AgentSkillDomain[] = execution
      ? execution.results.map((result) => result.agente_emissor.dominio)
      : pastSkillResults
          .map((item) => item.result?.agente_emissor.dominio)
          .filter((domain): domain is AgentSkillDomain => Boolean(domain))
    return [...new Set(domains)]
  }, [execution, pastSkillResults])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    llmApi
      .status()
      .then((status) => {
        setAllowedModels(status.allowed_models)
        setSelectedModel(status.model)
        if (status.daily_token_limit_per_user > 0) {
          setTokenUsage({ used: status.tokens_used_today, limit: status.daily_token_limit_per_user })
        }
      })
      .catch(() => {
        // Sem acesso ao status do LLM (ex.: perfil sem permissão) -- o backend
        // usa o modelo padrão configurado quando nenhum é enviado.
      })
    // A solicitação hoje não escolhe domínios explicitamente na tela de criação
    // (requested_domains chega vazio) -- nesse caso o Orquestrador consulta
    // todas as Agent Skills ativas do catálogo (ver _resolve_target_skills no
    // backend). Busca aqui a mesma lista, só para nomear as etapas reais da
    // animação de execução.
    agentSkillsApi
      .listSkills(true)
      .then((skills) => setActiveSkillDomains([...new Set(skills.map((skill) => skill.domain))]))
      .catch(() => setActiveSkillDomains([]))
  }, [])

  async function handleExecute() {
    if (!detail) return
    setExecuting(true)
    setExecutionError('')
    setSuccessMessage('')
    try {
      const result = await agentSkillsApi.execute(detail.technical_request.id, selectedModel || null)
      setExecution(result)
      await load()
      llmApi
        .status()
        .then((status) => {
          if (status.daily_token_limit_per_user > 0) {
            setTokenUsage({ used: status.tokens_used_today, limit: status.daily_token_limit_per_user })
          }
        })
        .catch(() => undefined)
      setSuccessMessage(
        result.verdict.approved
          ? 'Orquestração executada e aprovada pelo Quality Gate.'
          : 'Orquestração executada. O resultado aguarda revisão humana.',
      )
    } catch (caught) {
      setExecutionError(caught instanceof ApiError ? caught.message : 'Não foi possível executar a orquestração.')
    } finally {
      setExecuting(false)
    }
  }

  async function handleAskFollowUp(question: string, targetDomain: string | null) {
    if (!detail) return
    setAskingFollowUp(true)
    setFollowUpError('')
    try {
      const exchange = await agentSkillsApi.askFollowUp(
        detail.technical_request.id,
        question,
        targetDomain as AgentSkillDomain | null,
        selectedModel || null,
      )
      setFollowUps((current) => [...current, exchange])
      llmApi
        .status()
        .then((status) => {
          if (status.daily_token_limit_per_user > 0) {
            setTokenUsage({ used: status.tokens_used_today, limit: status.daily_token_limit_per_user })
          }
        })
        .catch(() => undefined)
    } catch (caught) {
      setFollowUpError(caught instanceof ApiError ? caught.message : 'Não foi possível registrar a pergunta.')
    } finally {
      setAskingFollowUp(false)
    }
  }

  async function handleContextSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!detail) return
    setSubmitting(true)
    setError('')
    setSuccessMessage('')
    try {
      await orchestrationApi.addContext(detail.technical_request.id, context)
      setContext('')
      await load()
      setSuccessMessage('Contexto complementado com sucesso.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível complementar o contexto.')
    } finally {
      setSubmitting(false)
    }
  }

  if (!detail && !error) {
    return <div className="workspace-loader">Carregando rastreabilidade…</div>
  }

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading workspace-detail-heading">
        <div>
          <Link className="workspace-back-link" to="/orchestrations">← Voltar para orquestrações</Link>
          <span className="workspace-eyebrow">TRACE ID: {traceId}</span>
          <h1>{detail?.technical_request.title ?? 'Orquestração'}</h1>
          {detail && <StatusBadge status={detail.technical_request.status} />}
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}
      {successMessage && <div className="alert alert-success">{successMessage}</div>}

      {detail && (
        <section className="workspace-detail-grid">
          <article className="workspace-panel workspace-request-summary">
            <div className="workspace-panel-heading">
              <div>
                <span className="workspace-card-kicker">SOLICITAÇÃO</span>
                <h2>Contexto da demanda</h2>
              </div>
              <code>{detail.technical_request.trace_id}</code>
            </div>

            <dl className="workspace-definition-list">
              <div><dt>Problema</dt><dd>{detail.technical_request.problem}</dd></div>
              <div><dt>Objetivo</dt><dd>{detail.technical_request.objective}</dd></div>
              <div><dt>Contexto</dt><dd>{detail.technical_request.context || 'Ainda não informado.'}</dd></div>
              <div>
                <dt>Restrições</dt>
                <dd>{detail.technical_request.restrictions.length ? detail.technical_request.restrictions.join(' · ') : 'Nenhuma'}</dd>
              </div>
              <div><dt>Etapa atual</dt><dd>{detail.run.current_stage}</dd></div>
            </dl>

            {detail.technical_request.status === 'AWAITING_CONTEXT' && (
              <form className="workspace-context-form" onSubmit={handleContextSubmit}>
                <label className="workspace-field">
                  Complementar contexto
                  <textarea
                    value={context}
                    onChange={(event) => setContext(event.target.value)}
                    rows={6}
                    minLength={10}
                    required
                    placeholder="Inclua tecnologias, módulos, artefatos, dependências e comportamento esperado."
                  />
                </label>
                <button className="workspace-primary-action" type="submit" disabled={submitting}>
                  {submitting ? 'Validando…' : 'Enviar complementação'}
                </button>
              </form>
            )}

            {detail.technical_request.status === 'QUALIFIED' && (
              <div className="workspace-execute-form">
                <label className="workspace-field">
                  Modelo de IA para a orquestração
                  <select value={selectedModel} onChange={(event) => setSelectedModel(event.target.value)}>
                    {allowedModels.length === 0 && <option value="">Padrão configurado</option>}
                    {allowedModels.map((model) => (
                      <option key={model} value={model}>
                        {model}
                      </option>
                    ))}
                  </select>
                  <small>Define qual modelo o Orquestrador usa para planejar e acionar as Agent Skills.</small>
                </label>
                {tokenUsage && <TokenUsageMeter used={tokenUsage.used} limit={tokenUsage.limit} />}
                {executionError && <div className="alert alert-error">{executionError}</div>}
                <button
                  className="workspace-primary-action"
                  type="button"
                  onClick={handleExecute}
                  disabled={executing || Boolean(tokenUsage && tokenUsage.used >= tokenUsage.limit)}
                >
                  {executing ? 'Executando…' : 'Executar orquestração'}
                </button>
                {executing && (
                  <OrchestrationThinkingAnimation
                    domains={
                      detail.technical_request.requested_domains.length > 0
                        ? (detail.technical_request.requested_domains as AgentSkillDomain[])
                        : activeSkillDomains
                    }
                    traceId={detail.technical_request.trace_id}
                  />
                )}
              </div>
            )}

            {execution ? (
              <ExecutionResultPanel execution={execution} />
            ) : (
              detail.technical_request.consolidated_response && (
                <ExecutionResultPanel
                  execution={{
                    results: pastSkillResults.map((item) => item.result).filter((item) => item !== null),
                    verdict: {
                      approved: detail.technical_request.consolidated_response.quality_gate_approved,
                      requires_human_review: detail.technical_request.consolidated_response.requires_human_review,
                      reasons: [],
                    },
                    invocations_count: pastSkillResults.length,
                    consolidated_response: detail.technical_request.consolidated_response,
                  }}
                />
              )
            )}

            {detail.technical_request.consolidated_response && (
              <div className="workspace-follow-up-section">
                {followUps.map((exchange) => (
                  <FollowUpExchangeCard key={exchange.id} exchange={exchange} />
                ))}
                <FollowUpForm
                  participatingDomains={participatingDomains}
                  onAsk={handleAskFollowUp}
                  submitting={askingFollowUp}
                  error={followUpError}
                />
              </div>
            )}
          </article>

          <article className="workspace-panel workspace-timeline-panel">
            <div className="workspace-panel-heading">
              <div>
                <span className="workspace-card-kicker">RASTREABILIDADE</span>
                <h2>Linha do tempo</h2>
              </div>
              <span>{detail.events.length} eventos</span>
            </div>

            <div className="workspace-timeline">
              {detail.events.map((event) => (
                <article key={event.id} className="workspace-timeline-event">
                  <span className="workspace-timeline-marker">{event.sequence_number}</span>
                  <div>
                    <span>{event.actor}</span>
                    <h3>{event.title}</h3>
                    <p>{event.message}</p>
                    <small>{new Date(event.created_at).toLocaleString('pt-BR')}</small>
                  </div>
                </article>
              ))}
            </div>
          </article>
        </section>
      )}
    </div>
  )
}
