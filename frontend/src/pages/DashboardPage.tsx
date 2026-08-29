import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { DashboardSummary, dashboardApi } from '../api/dashboardApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'
import { ActionBanner } from '../components/dashboard/ActionBanner'
import { ActivityFeed } from '../components/dashboard/ActivityFeed'
import { EcosystemFlowCard } from '../components/dashboard/EcosystemFlowCard'
import { MetricCard } from '../components/dashboard/MetricCard'
import { RecentRequestsTable } from '../components/dashboard/RecentRequestsTable'

export function DashboardPage() {
  const { user } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    dashboardApi
      .summary()
      .then(setSummary)
      .catch((caught) => {
        setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar o painel.')
      })
  }, [])

  const successRate = summary ? `${Math.round(summary.success_rate * 100)}%` : '—'
  const awaitingContext = summary?.awaiting_context ?? 0
  const recentRequests = (summary?.recent_requests ?? []).slice(0, 5)

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">VISÃO GERAL</span>
          <h1>Olá, {user?.name.split(' ')[0]}.</h1>
          <p>Acompanhe solicitações, estados e eventos do ecossistema de agentes.</p>
        </div>
        <Link className="workspace-primary-action" to="/requests/new">+ Nova solicitação</Link>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      {summary && (
        <div className="fade-up" style={{ animationDelay: '0.06s' }}>
          <ActionBanner requests={summary.recent_requests} />
        </div>
      )}

      <section className="workspace-metric-grid fade-up" style={{ animationDelay: '0.12s' }} aria-label="Indicadores da orquestração">
        <MetricCard
          icon="◎"
          label="Orquestrações em execução"
          value={summary?.running_orchestrations ?? '—'}
          helper="Qualificadas ou em processamento"
          tone="accent"
        />
        <MetricCard
          icon="◷"
          label="Aguardando contexto"
          value={summary?.awaiting_context ?? '—'}
          helper="Dependem de complementação"
          tone="warning"
          highlight={awaitingContext > 0}
        />
        <MetricCard
          icon="▤"
          label="Solicitações registradas"
          value={summary?.orchestration_executions ?? '—'}
          helper="Cada uma possui Trace ID"
          tone="info"
        />
        <MetricCard
          icon="✓"
          label="Taxa de sucesso"
          value={successRate}
          helper="Calculada após fluxos concluídos"
          tone="success"
        />
      </section>

      <section className="workspace-dashboard-grid fade-up" style={{ animationDelay: '0.18s' }}>
        <article className="workspace-panel">
          <div className="workspace-panel-heading">
            <div>
              <span className="workspace-card-kicker">FLUXOS RECENTES</span>
              <h2>Solicitações técnicas</h2>
            </div>
            <Link to="/orchestrations">Ver todas →</Link>
          </div>
          <RecentRequestsTable requests={recentRequests} showToolbar />
        </article>

        <div className="workspace-side-column">
          <article className="workspace-panel">
            <div className="workspace-panel-heading">
              <div>
                <span className="workspace-card-kicker">RASTREABILIDADE</span>
                <h2>Atividade recente</h2>
              </div>
            </div>
            <ActivityFeed events={summary?.recent_orchestration_events ?? []} />
          </article>

          <EcosystemFlowCard />
        </div>
      </section>
    </div>
  )
}
