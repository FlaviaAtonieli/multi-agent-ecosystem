import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { DashboardSummary, dashboardApi } from '../api/dashboardApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'
import { ActivityFeed } from '../components/dashboard/ActivityFeed'
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

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading">
        <div>
          <span className="workspace-eyebrow">VISÃO GERAL</span>
          <h1>Olá, {user?.name.split(' ')[0]}.</h1>
          <p>Acompanhe solicitações, estados e eventos do ecossistema de agentes.</p>
        </div>
        <Link className="workspace-primary-action" to="/requests/new">+ Nova solicitação</Link>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <section className="workspace-metric-grid" aria-label="Indicadores da orquestração">
        <MetricCard
          label="Orquestrações em execução"
          value={summary?.running_orchestrations ?? '—'}
          helper="Qualificadas ou em processamento"
          tone="accent"
        />
        <MetricCard
          label="Aguardando contexto"
          value={summary?.awaiting_context ?? '—'}
          helper="Dependem de complementação"
          tone="warning"
        />
        <MetricCard
          label="Solicitações registradas"
          value={summary?.orchestration_executions ?? '—'}
          helper="Cada uma possui Trace ID"
        />
        <MetricCard
          label="Taxa de sucesso"
          value={successRate}
          helper="Será calculada após fluxos concluídos"
        />
      </section>

      <section className="workspace-dashboard-grid">
        <article className="workspace-panel workspace-panel-wide">
          <div className="workspace-panel-heading">
            <div>
              <span className="workspace-card-kicker">FLUXOS RECENTES</span>
              <h2>Solicitações técnicas</h2>
            </div>
            <Link to="/orchestrations">Ver todas</Link>
          </div>
          <RecentRequestsTable requests={summary?.recent_requests ?? []} />
        </article>

        <article className="workspace-panel">
          <div className="workspace-panel-heading">
            <div>
              <span className="workspace-card-kicker">RASTREABILIDADE</span>
              <h2>Atividade recente</h2>
            </div>
          </div>
          <ActivityFeed events={summary?.recent_orchestration_events ?? []} />
        </article>
      </section>
    </div>
  )
}
