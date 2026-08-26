import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { DashboardSummary, dashboardApi } from '../api/dashboardApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'
import { Brand } from '../components/Brand'

const eventLabels: Record<string, string> = {
  AUTH_REGISTER_SUCCESS: 'Conta criada',
  AUTH_LOGIN_SUCCESS: 'Login realizado',
  AUTH_LOGOUT: 'Sessão encerrada',
  AUTH_LOGOUT_ALL: 'Todas as sessões encerradas',
  AUTH_SESSION_RENEWED: 'Sessão renovada',
  AUTH_SESSION_REVOKED: 'Sessão revogada',
  ADMIN_USER_STATUS_CHANGED: 'Status de usuário alterado',
}

export function DashboardPage() {
  const navigate = useNavigate()
  const { user, logout, logoutAll } = useAuth()
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    dashboardApi
      .summary()
      .then(setSummary)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar o painel.'))
  }, [])

  async function handleLogout(allSessions: boolean) {
    setBusy(true)
    try {
      if (allSessions) await logoutAll()
      else await logout()
      navigate('/login', { replace: true })
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="dashboard-page">
      <header className="topbar">
        <Brand />
        <div className="topbar-user">
          <div>
            <strong>{user?.name}</strong>
            <small>{user?.role === 'ADMIN' ? 'Administrador' : 'Usuário técnico'}</small>
          </div>
          <button className="ghost-button" onClick={() => handleLogout(false)} disabled={busy}>Sair</button>
        </div>
      </header>

      <div className="dashboard-shell">
        <section className="welcome-row">
          <div>
            <span className="eyebrow">VISÃO GERAL</span>
            <h1>Olá, {user?.name.split(' ')[0]}.</h1>
            <p className="muted">A base de autenticação está funcionando. O próximo passo é acoplar o catálogo de Agent Skills.</p>
          </div>
          <div className="secure-badge"><span /> Sessão protegida</div>
        </section>

        {error && <div className="alert alert-error">{error}</div>}

        <section className="metric-grid" aria-label="Resumo do ambiente">
          <article className="metric-card">
            <span>Sessões ativas</span>
            <strong>{summary?.active_sessions ?? '—'}</strong>
            <small>Persistidas e revogáveis</small>
          </article>
          <article className="metric-card">
            <span>Agent Skills</span>
            <strong>{summary?.registered_agent_skills ?? '—'}</strong>
            <small>Catálogo será o próximo módulo</small>
          </article>
          <article className="metric-card">
            <span>Execuções</span>
            <strong>{summary?.orchestration_executions ?? '—'}</strong>
            <small>Nenhuma simulação exibida</small>
          </article>
          {summary?.total_users !== null && summary?.total_users !== undefined && (
            <article className="metric-card">
              <span>Usuários</span>
              <strong>{summary.total_users}</strong>
              <small>Visível para administradores</small>
            </article>
          )}
        </section>

        <section className="dashboard-grid">
          <article className="panel">
            <div className="panel-heading">
              <div>
                <span className="card-kicker">Próxima evolução</span>
                <h2>Catálogo de Agent Skills</h2>
              </div>
              <span className="status-pill">Planejado</span>
            </div>
            <p>
              Esta base já entrega identidade, sessão e auditoria. O próximo módulo pode reutilizar o usuário autenticado
              para importar o <code>modelo.md</code>, validar contratos e registrar a skill.
            </p>
            <div className="flow-preview">
              <span>Login</span><b>→</b><span>Catálogo</span><b>→</b><span>Orquestração</span><b>→</b><span>Trace ID</span>
            </div>
            <button className="secondary-button" disabled>Ambiente de orquestração em construção</button>
          </article>

          <article className="panel">
            <div className="panel-heading">
              <div>
                <span className="card-kicker">Segurança</span>
                <h2>Eventos recentes</h2>
              </div>
            </div>
            <div className="event-list">
              {summary?.recent_security_events.length ? (
                summary.recent_security_events.map((event, index) => (
                  <div className="event-item" key={`${event.event_type}-${event.created_at}-${index}`}>
                    <span className="event-dot" />
                    <div>
                      <strong>{eventLabels[event.event_type] ?? event.event_type}</strong>
                      <small>{new Date(event.created_at).toLocaleString('pt-BR')}</small>
                    </div>
                  </div>
                ))
              ) : (
                <p className="muted">Os eventos desta conta aparecerão aqui.</p>
              )}
            </div>
          </article>
        </section>

        <section className="security-strip">
          <div><strong>Argon2</strong><small>Hash de senhas</small></div>
          <div><strong>HttpOnly</strong><small>Cookie de sessão</small></div>
          <div><strong>CSRF</strong><small>Proteção em operações</small></div>
          <div><strong>RBAC</strong><small>Perfis USER e ADMIN</small></div>
          <button className="danger-link" onClick={() => handleLogout(true)} disabled={busy}>Encerrar todas as sessões</button>
        </section>
      </div>
    </main>
  )
}
