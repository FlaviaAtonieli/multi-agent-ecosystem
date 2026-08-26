import { FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { agentSkillsApi, OrchestrationExecutionResult } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'
import { llmApi } from '../api/llmApi'
import { OrchestrationDetail, orchestrationApi } from '../api/orchestrationApi'
import { ExecutionResultPanel } from '../components/orchestration/ExecutionResultPanel'
import { StatusBadge } from '../components/orchestration/StatusBadge'

export function OrchestrationPage() {
  const { traceId = '' } = useParams()
  const [detail, setDetail] = useState<OrchestrationDetail | null>(null)
  const [context, setContext] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [allowedModels, setAllowedModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [executing, setExecuting] = useState(false)
  const [executionError, setExecutionError] = useState('')
  const [execution, setExecution] = useState<OrchestrationExecutionResult | null>(null)

  const load = useCallback(async () => {
    try {
      setDetail(await orchestrationApi.getOrchestration(traceId))
      setError('')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar a orquestração.')
    }
  }, [traceId])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    llmApi
      .status()
      .then((status) => {
        setAllowedModels(status.allowed_models)
        setSelectedModel(status.model)
      })
      .catch(() => {
        // Sem acesso ao status do LLM (ex.: perfil sem permissão) -- o backend
        // usa o modelo padrão configurado quando nenhum é enviado.
      })
  }, [])

  async function handleExecute() {
    if (!detail) return
    setExecuting(true)
    setExecutionError('')
    try {
      const result = await agentSkillsApi.execute(detail.technical_request.id, selectedModel || null)
      setExecution(result)
      await load()
    } catch (caught) {
      setExecutionError(caught instanceof ApiError ? caught.message : 'Não foi possível executar a orquestração.')
    } finally {
      setExecuting(false)
    }
  }

  async function handleContextSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!detail) return
    setSubmitting(true)
    setError('')
    try {
      await orchestrationApi.addContext(detail.technical_request.id, context)
      setContext('')
      await load()
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
                {executionError && <div className="alert alert-error">{executionError}</div>}
                <button className="workspace-primary-action" type="button" onClick={handleExecute} disabled={executing}>
                  {executing ? 'Executando…' : 'Executar orquestração'}
                </button>
              </div>
            )}

            {execution ? (
              <ExecutionResultPanel execution={execution} />
            ) : (
              detail.technical_request.consolidated_response && (
                <div className="workspace-execution">
                  <p className="workspace-execution-synthesis">
                    {detail.technical_request.consolidated_response.technical_synthesis}
                  </p>
                </div>
              )
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
