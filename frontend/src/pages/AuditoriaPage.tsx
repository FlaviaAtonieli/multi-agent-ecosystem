import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AuditEvent, AuditEventPage, auditApi } from '../api/auditApi'
import { ApiError } from '../api/http'

const actorLabels: Record<string, string> = {
  USER: 'Usuário',
  INTERACTION_GUIDE: 'Orientador de Interação',
  ORCHESTRATOR: 'Orquestrador',
  ADVISORY_AGENT: 'Agent Skill',
  REVIEWER: 'Revisor',
  RETRIEVAL_AGENT: 'RAG',
  TECHNICAL_PLANNER: 'Planejador Técnico',
}

const actorTones: Record<string, string> = {
  USER: 'violet',
  INTERACTION_GUIDE: 'amber',
  ORCHESTRATOR: 'cyan',
  ADVISORY_AGENT: 'sky',
  REVIEWER: 'green',
  RETRIEVAL_AGENT: 'sky',
  TECHNICAL_PLANNER: 'sky',
}

const knownActors = Object.keys(actorLabels)

function toCsv(events: AuditEvent[]): string {
  const header = ['Evento', 'Origem', 'Solicitação', 'Trace ID', 'Data/Hora']
  const rows = events.map((event) => [
    event.title,
    actorLabels[event.actor] ?? event.actor,
    event.request_title,
    event.request_trace_id,
    new Date(event.created_at).toLocaleString('pt-BR'),
  ])
  return [header, ...rows]
    .map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(','))
    .join('\n')
}

function downloadCsv(csv: string) {
  const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `auditoria-${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export function AuditoriaPage() {
  const [page, setPage] = useState<AuditEventPage | null>(null)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [actor, setActor] = useState<string>('ALL')
  const [days, setDays] = useState(7)

  useEffect(() => {
    const handle = setTimeout(() => {
      auditApi
        .listEvents({ days, actor: actor === 'ALL' ? undefined : actor, search: search || undefined, limit: 100 })
        .then(setPage)
        .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar a trilha de auditoria.'))
    }, 250)
    return () => clearTimeout(handle)
  }, [days, actor, search])

  const actorsPresent = useMemo(() => {
    if (!page) return knownActors
    const present = new Set(page.items.map((item) => item.actor))
    return knownActors.filter((key) => present.has(key))
  }, [page])

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">AUDITORIA</span>
          <h1>Trilha de auditoria</h1>
          <p>Histórico completo de eventos do ecossistema, por agente e por solicitação, para conformidade e rastreabilidade.</p>
        </div>
        <button
          type="button"
          className="workspace-secondary-action"
          disabled={!page || page.items.length === 0}
          onClick={() => page && downloadCsv(toCsv(page.items))}
        >
          ↓ Exportar CSV
        </button>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="workspace-metric-grid fade-up" style={{ animationDelay: '0.08s' }} aria-label="Indicadores de auditoria">
        <article className="workspace-metric-card">
          <span>Eventos registrados hoje</span>
          <strong>{page?.stats.events_today ?? '—'}</strong>
        </article>
        <article className="workspace-metric-card">
          <span>Decisões automatizadas</span>
          <strong>{page?.stats.automated_decisions_today ?? '—'}</strong>
        </article>
        <article className="workspace-metric-card">
          <span>Intervenções manuais</span>
          <strong>{page?.stats.manual_interventions_today ?? '—'}</strong>
        </article>
        <article className={`workspace-metric-card${page && page.stats.compliance_alerts_today > 0 ? ' workspace-metric-card-alert' : ''}`}>
          <span>Alertas de conformidade</span>
          <strong className={page && page.stats.compliance_alerts_today === 0 ? 'workspace-metric-value-success' : 'workspace-metric-value-danger'}>
            {page?.stats.compliance_alerts_today ?? '—'}
          </strong>
        </article>
      </section>

      <div className="workspace-orchestrations-toolbar fade-up" style={{ animationDelay: '0.14s' }}>
        <input
          type="search"
          placeholder="Buscar por evento ou Trace ID..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <div className="workspace-filter-chips" role="group" aria-label="Filtrar por agente">
          <button type="button" className={`workspace-filter-chip${actor === 'ALL' ? ' active' : ''}`} onClick={() => setActor('ALL')}>
            Todos os agentes
          </button>
          {actorsPresent.map((key) => (
            <button
              key={key}
              type="button"
              className={`workspace-filter-chip${actor === key ? ' active' : ''}`}
              onClick={() => setActor(key)}
            >
              {actorLabels[key]}
            </button>
          ))}
        </div>

        <select value={days} onChange={(event) => setDays(Number(event.target.value))}>
          <option value={7}>Últimos 7 dias</option>
          <option value={14}>Últimos 14 dias</option>
          <option value={30}>Últimos 30 dias</option>
          <option value={90}>Últimos 90 dias</option>
        </select>
      </div>

      <article className="workspace-panel">
        {!page || page.items.length === 0 ? (
          <div className="workspace-empty">
            {page ? 'Nenhum evento corresponde ao filtro atual.' : 'Carregando…'}
          </div>
        ) : (
          <div className="workspace-table-wrap">
            <table className="workspace-table workspace-table-audit">
              <thead>
                <tr>
                  <th>Evento</th>
                  <th>Origem</th>
                  <th>Solicitação</th>
                  <th>Trace ID</th>
                  <th>Data/Hora</th>
                </tr>
              </thead>
              <tbody>
                {page.items.map((event) => (
                  <tr key={event.id}>
                    <td className="workspace-audit-event-name">{event.title}</td>
                    <td>
                      <span className={`workspace-actor-badge workspace-actor-badge-${actorTones[event.actor] ?? 'sky'}`}>
                        {actorLabels[event.actor] ?? event.actor}
                      </span>
                    </td>
                    <td>
                      <Link to={`/orchestrations/${event.request_trace_id}`}>{event.request_title}</Link>
                    </td>
                    <td><code>{event.request_trace_id}</code></td>
                    <td>{new Date(event.created_at).toLocaleString('pt-BR')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </div>
  )
}
