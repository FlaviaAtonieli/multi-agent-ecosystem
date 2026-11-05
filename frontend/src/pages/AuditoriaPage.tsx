import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AuditEvent, AuditEventPage, auditApi } from '../api/auditApi'
import { ApiError } from '../api/http'
import { OnboardingTour, TourStep } from '../components/onboarding/OnboardingTour'


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

// Os indicadores seguem as regras de backend/app/api/v1/endpoints/audit.py.
const helpSteps: TourStep[] = [
  {
    selector: '[data-tour="audit-intro"]',
    title: 'Para que serve',
    description:
      'Cada passo das suas solicitações fica registrado aqui: quem agiu, em qual solicitação e quando. É o que permite explicar depois como uma resposta da IA foi construída, conferir se as regras foram seguidas e responder a pedidos de transparência, como os previstos na LGPD.',
  },
  {
    selector: '[data-tour="audit-metrics"]',
    title: 'O que os números contam',
    description:
      'Contagens de hoje. Decisões automatizadas são as do Orientador, do Orquestrador, das skills e do RAG. Intervenções manuais são as feitas por pessoas. Alertas de conformidade são uma falha de IA, uma falha de skill ou uma resposta rejeitada na revisão humana.',
  },
  {
    selector: '[data-tour="audit-filters"]',
    title: 'Encontre um evento',
    description: 'Busque pelo nome do evento ou pelo Trace ID, filtre por agente e escolha o período, de 7 a 90 dias.',
  },
  {
    selector: '[data-tour="audit-table"]',
    title: 'Do evento à análise',
    description:
      'Clique na solicitação para abrir a linha do tempo completa, com cada etapa, os agentes acionados e o resultado.',
  },
  {
    selector: '[data-tour="audit-export"]',
    title: 'Leve para fora',
    description:
      'Exporte em CSV para relatórios ou auditorias externas. Entram os eventos carregados na tela, com os filtros atuais.',
  },
]

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
  const [showHelp, setShowHelp] = useState(false)

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
      {showHelp && <OnboardingTour steps={helpSteps} skipLabel="Fechar ajuda" onFinish={() => setShowHelp(false)} />}

      <section className="workspace-page-heading fade-up">
        <div data-tour="audit-intro">
          <span className="workspace-eyebrow">AUDITORIA</span>
          <h1>Trilha de auditoria</h1>
          <p>Histórico de eventos das suas solicitações, por agente, para conformidade e rastreabilidade.</p>
        </div>
        <div className="workspace-page-heading-actions">
          <button
            type="button"
            className="workspace-help-button"
            aria-label="Como usar a auditoria"
            title="Como usar a auditoria"
            onClick={() => setShowHelp(true)}
          >
            !
          </button>
          <button
          type="button"
          data-tour="audit-export"
          className="workspace-secondary-action"
          disabled={!page || page.items.length === 0}
          onClick={() => page && downloadCsv(toCsv(page.items))}
        >
          ↓ Exportar CSV
          </button>
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <section data-tour="audit-metrics" className="workspace-metric-grid fade-up" style={{ animationDelay: '0.08s' }} aria-label="Indicadores de auditoria">
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

      <div data-tour="audit-filters" className="workspace-orchestrations-toolbar fade-up" style={{ animationDelay: '0.14s' }}>
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

        <select aria-label="Período da auditoria" value={days} onChange={(event) => setDays(Number(event.target.value))}>
          <option value={7}>Últimos 7 dias</option>
          <option value={14}>Últimos 14 dias</option>
          <option value={30}>Últimos 30 dias</option>
          <option value={90}>Últimos 90 dias</option>
        </select>
      </div>

      <article data-tour="audit-table" className="workspace-panel">
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
