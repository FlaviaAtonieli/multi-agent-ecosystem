import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { AgentSkillDomain, agentSkillsApi, FollowUpExchange } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'
import { llmApi } from '../api/llmApi'
import { AgentSkillInvocationResult, OrchestrationDetail, OrchestrationEvent, orchestrationApi } from '../api/orchestrationApi'
import { ArtifactsPanel } from '../components/orchestration/ArtifactsPanel'
import { AttachmentsSection } from '../components/orchestration/AttachmentsSection'
import { ExecutionResultPanel } from '../components/orchestration/ExecutionResultPanel'
import { FollowUpExchangeCard } from '../components/orchestration/FollowUpExchangeCard'
import { FollowUpForm } from '../components/orchestration/FollowUpForm'
import { HumanReviewPanel } from '../components/orchestration/HumanReviewPanel'
import { OrchestrationThinkingAnimation } from '../components/orchestration/OrchestrationThinkingAnimation'
import { StatusBadge } from '../components/orchestration/StatusBadge'
import { TokenUsageMeter } from '../components/orchestration/TokenUsageMeter'
import { CollapsibleSection } from '../components/shared/CollapsibleSection'

const POLL_INTERVAL_MS = 4000
const FOLLOW_UP_EVENT_TYPES = ['FOLLOW_UP_QUESTION_ASKED', 'FOLLOW_UP_RESPONSE_RECEIVED', 'FOLLOW_UP_FAILED']

function latestFollowUpEvent(events: OrchestrationEvent[]) {
  return [...events].reverse().find((event) => FOLLOW_UP_EVENT_TYPES.includes(event.event_type))
}

export function OrchestrationPage() {
  const { traceId = '' } = useParams()
  const location = useLocation()
  const failedAttachmentUploads = (location.state as { failedAttachmentUploads?: string[] } | null)
    ?.failedAttachmentUploads
  const [detail, setDetail] = useState<OrchestrationDetail | null>(null)
  const [pastSkillResults, setPastSkillResults] = useState<AgentSkillInvocationResult[]>([])
  const [followUps, setFollowUps] = useState<FollowUpExchange[]>([])
  const [context, setContext] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [allowedModels, setAllowedModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [tokenUsage, setTokenUsage] = useState<{ used: number; limit: number } | null>(null)
  const [starting, setStarting] = useState(false)
  const [confirmingCancel, setConfirmingCancel] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [askingFollowUp, setAskingFollowUp] = useState(false)
  const [followUpError, setFollowUpError] = useState('')
  const previousStatus = useRef<string | null>(null)
  const previousFollowUpPending = useRef(false)

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
    const domains = pastSkillResults
      .map((item) => item.result?.agente_emissor.dominio)
      .filter((domain): domain is AgentSkillDomain => Boolean(domain))
    return [...new Set(domains)]
  }, [pastSkillResults])

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
  }, [])

  const status = detail?.technical_request.status
  const running = status === 'RUNNING'

  // A execução roda em segundo plano no backend: enquanto durar, acompanha o
  // andamento pela linha do tempo. Uma falha pontual de rede não interrompe o
  // acompanhamento, a próxima consulta tenta de novo.
  const latestFollowUp = detail ? latestFollowUpEvent(detail.events) : undefined
  const followUpPendingSince =
    latestFollowUp?.event_type === 'FOLLOW_UP_QUESTION_ASKED' ? latestFollowUp.created_at : null
  const followUpPending = followUpPendingSince !== null

  useEffect(() => {
    if (!running && !followUpPending) return
    const timer = window.setInterval(() => {
      orchestrationApi.getOrchestration(traceId).then(setDetail).catch(() => undefined)
    }, POLL_INTERVAL_MS)
    return () => window.clearInterval(timer)
  }, [running, followUpPending, traceId])

  const failedFollowUpMessage = latestFollowUp?.event_type === 'FOLLOW_UP_FAILED' ? latestFollowUp.message : ''

  useEffect(() => {
    const finished = previousFollowUpPending.current && !followUpPending
    previousFollowUpPending.current = followUpPending
    if (!finished) return

    load()
    llmApi
      .status()
      .then((llmStatus) => {
        if (llmStatus.daily_token_limit_per_user > 0) {
          setTokenUsage({ used: llmStatus.tokens_used_today, limit: llmStatus.daily_token_limit_per_user })
        }
      })
      .catch(() => undefined)
    setFollowUpError(failedFollowUpMessage)
  }, [followUpPending, failedFollowUpMessage, load])

  useEffect(() => {
    const finished = previousStatus.current === 'RUNNING' && status !== undefined && status !== 'RUNNING'
    previousStatus.current = status ?? null
    if (!finished) return

    load()
    llmApi
      .status()
      .then((llmStatus) => {
        if (llmStatus.daily_token_limit_per_user > 0) {
          setTokenUsage({ used: llmStatus.tokens_used_today, limit: llmStatus.daily_token_limit_per_user })
        }
      })
      .catch(() => undefined)
    if (status === 'CANCELLED') {
      setExecutionError(
        'Você interrompeu a execução. Se faltou alguma informação, complemente o contexto abaixo e execute de novo.',
      )
      setContext(detail?.technical_request.context ?? '')
    } else if (status === 'FAILED') {
      setExecutionError('A execução foi interrompida. Veja a linha do tempo e tente executar novamente.')
    } else {
      setSuccessMessage(
        status === 'COMPLETED'
          ? 'Orquestração executada e aprovada pelo Quality Gate.'
          : 'Orquestração executada. O resultado aguarda revisão humana.',
      )
    }
    // A resposta aparece no topo da página (antes do contexto, ver hasResult) --
    // leva o usuário até lá em vez de deixá-lo onde estava rolado durante a execução.
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }, [status, load])

  async function handleCancel() {
    if (!detail) return
    setCancelling(true)
    setExecutionError('')
    try {
      await agentSkillsApi.cancel(detail.technical_request.id)
      setConfirmingCancel(false)
      await load()
    } catch (caught) {
      setExecutionError(caught instanceof ApiError ? caught.message : 'Não foi possível interromper a execução.')
    } finally {
      setCancelling(false)
    }
  }

  async function handleExecute() {
    if (!detail) return
    setStarting(true)
    setExecutionError('')
    setSuccessMessage('')
    try {
      await agentSkillsApi.start(detail.technical_request.id, selectedModel || null)
      await load()
    } catch (caught) {
      setExecutionError(caught instanceof ApiError ? caught.message : 'Não foi possível executar a orquestração.')
    } finally {
      setStarting(false)
    }
  }

  async function handleAskFollowUp(question: string, targetDomain: string | null) {
    if (!detail) return
    setAskingFollowUp(true)
    setFollowUpError('')
    try {
      await agentSkillsApi.startFollowUp(
        detail.technical_request.id,
        question,
        targetDomain as AgentSkillDomain | null,
        selectedModel || null,
      )
      await load()
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

  const hasResult = Boolean(detail?.technical_request.consolidated_response) && !running

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

      {(error || successMessage || (failedAttachmentUploads && failedAttachmentUploads.length > 0)) && (
        <div className="workspace-orchestration-alerts">
          {error && <div className="alert alert-error">{error}</div>}
          {successMessage && <div className="alert alert-success">{successMessage}</div>}
          {failedAttachmentUploads && failedAttachmentUploads.length > 0 && (
            <div className="alert alert-error">
              Não foi possível anexar: {failedAttachmentUploads.join(', ')}. A solicitação foi criada normalmente —
              tente anexar de novo abaixo.
            </div>
          )}
        </div>
      )}

      {detail && (
        <section className="workspace-orchestration-flow">
          {running && (
            <>
              <OrchestrationThinkingAnimation events={detail.events} traceId={detail.technical_request.trace_id} />
              <div className="workspace-cancel-row">
                {confirmingCancel ? (
                  <>
                    <span>As respostas ainda não recebidas serão descartadas.</span>
                    <button
                      type="button"
                      className="workspace-secondary-action"
                      disabled={cancelling}
                      onClick={() => setConfirmingCancel(false)}
                    >
                      Continuar executando
                    </button>
                    <button type="button" className="workspace-danger-action" disabled={cancelling} onClick={handleCancel}>
                      {cancelling ? 'Interrompendo…' : 'Confirmar interrupção'}
                    </button>
                  </>
                ) : (
                  <button type="button" className="workspace-secondary-action" onClick={() => setConfirmingCancel(true)}>
                    Interromper execução
                  </button>
                )}
                {executionError && <div className="alert alert-error">{executionError}</div>}
              </div>
            </>
          )}

          {hasResult && (
            <article className="workspace-panel workspace-result-panel">
              <div className="workspace-panel-heading">
                <div>
                  <span className="workspace-card-kicker">RESULTADO</span>
                  <h2>Resposta consolidada</h2>
                </div>
                <code>{detail.technical_request.trace_id}</code>
              </div>
              {detail.technical_request.consolidated_response && (
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
              )}
              <ArtifactsPanel traceId={detail.technical_request.trace_id} refreshKey={followUps.length} />
            </article>
          )}

          {detail.technical_request.status === 'VALIDATING' && (
            <HumanReviewPanel
              requestId={detail.technical_request.id}
              onReviewed={async (decision) => {
                await load()
                setSuccessMessage(
                  decision === 'approve'
                    ? 'Resposta aprovada. A orquestração foi concluída.'
                    : 'Resposta rejeitada. A justificativa ficou registrada na linha do tempo.',
                )
                window.scrollTo({ top: 0, behavior: 'smooth' })
              }}
            />
          )}

          <CollapsibleSection
            title="Contexto da demanda"
            subtitle={hasResult ? detail.technical_request.trace_id : undefined}
            defaultOpen={!hasResult}
          >
            {!hasResult && (
              <div className="workspace-panel-heading">
                <div>
                  <span className="workspace-card-kicker">SOLICITAÇÃO</span>
                </div>
                <code>{detail.technical_request.trace_id}</code>
              </div>
            )}

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

            <AttachmentsSection requestId={detail.technical_request.id} />

            {(status === 'AWAITING_CONTEXT' || status === 'CANCELLED') && (
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

            {(status === 'QUALIFIED' || status === 'FAILED' || status === 'CANCELLED') && (
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
                  disabled={starting || Boolean(tokenUsage && tokenUsage.used >= tokenUsage.limit)}
                >
                  {starting ? 'Iniciando…' : status === 'FAILED' || status === 'CANCELLED' ? 'Executar novamente' : 'Executar orquestração'}
                </button>
              </div>
            )}
          </CollapsibleSection>

          {detail.technical_request.consolidated_response && (
            <article className="workspace-panel workspace-follow-up-panel">
              <div className="workspace-panel-heading">
                <div>
                  <span className="workspace-card-kicker">CONTINUAR A ANÁLISE</span>
                  <h2>Perguntas de acompanhamento</h2>
                </div>
              </div>
              <div className="workspace-follow-up-section">
                {followUps.map((exchange) => (
                  <FollowUpExchangeCard key={exchange.id} exchange={exchange} />
                ))}
                <FollowUpForm
                  participatingDomains={participatingDomains}
                  onAsk={handleAskFollowUp}
                  submitting={askingFollowUp}
                  pendingSince={followUpPendingSince}
                  error={followUpError}
                />
              </div>
            </article>
          )}

          <CollapsibleSection title="Linha do tempo" subtitle={`${detail.events.length} eventos · rastreabilidade`} defaultOpen={false}>
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
          </CollapsibleSection>
        </section>
      )}
    </div>
  )
}
