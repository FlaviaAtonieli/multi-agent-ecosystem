import { FormEvent, useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { OrchestrationDetail, orchestrationApi } from '../api/orchestrationApi'
import { StatusBadge } from '../components/orchestration/StatusBadge'

export function OrchestrationPage() {
  const { traceId = '' } = useParams()
  const [detail, setDetail] = useState<OrchestrationDetail | null>(null)
  const [context, setContext] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

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
