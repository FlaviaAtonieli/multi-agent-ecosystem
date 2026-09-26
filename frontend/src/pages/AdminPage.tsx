import { useEffect, useState } from 'react'
import { AdminUser, adminApi } from '../api/adminApi'
import { User } from '../api/authApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

const roleOptions: Array<{ value: User['role']; label: string }> = [
  { value: 'USER', label: 'Usuário' },
  { value: 'TECHNICIAN', label: 'Usuário técnico' },
  { value: 'REVIEWER', label: 'Revisor' },
  { value: 'ADMIN', label: 'Administrador' },
]

function tokenUsageTone(user: AdminUser): 'default' | 'warning' | 'danger' {
  if (user.daily_token_limit_per_user <= 0) return 'default'
  if (user.tokens_used_today >= user.daily_token_limit_per_user) return 'danger'
  if (user.tokens_used_today / user.daily_token_limit_per_user >= 0.7) return 'warning'
  return 'default'
}

export function AdminPage() {
  const { user: currentUser } = useAuth()
  const [users, setUsers] = useState<AdminUser[]>([])
  const [error, setError] = useState('')
  const [pendingId, setPendingId] = useState<string | null>(null)

  function load() {
    adminApi
      .listUsers()
      .then(setUsers)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar os usuários.'))
  }

  useEffect(load, [])

  async function changeRole(user: AdminUser, role: User['role']) {
    if (role === user.role) return
    setPendingId(user.id)
    setError('')
    try {
      const updated = await adminApi.updateRole(user.id, role)
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível atualizar o papel do usuário.')
    } finally {
      setPendingId(null)
    }
  }

  async function toggleStatus(user: AdminUser) {
    setPendingId(user.id)
    setError('')
    try {
      const updated = await adminApi.updateStatus(user.id, !user.is_active)
      setUsers((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível atualizar o status do usuário.')
    } finally {
      setPendingId(null)
    }
  }

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">ADMINISTRAÇÃO</span>
          <h1>Usuários e permissões</h1>
          <p>Gerencie papéis, acesso e uso diário de tokens das contas registradas no ecossistema.</p>
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <article className="workspace-panel">
        {users.length === 0 ? (
          <div className="workspace-empty">Nenhum usuário registrado ainda.</div>
        ) : (
          <div className="workspace-table-wrap">
            <table className="workspace-table workspace-table-admin">
              <thead>
                <tr>
                  <th>Usuário</th>
                  <th>Papel</th>
                  <th>Status</th>
                  <th>Tokens hoje</th>
                  <th>Registrado em</th>
                  <th>Ações</th>
                </tr>
              </thead>
              <tbody>
                {users.map((user) => {
                  const isSelf = user.id === currentUser?.id
                  const tone = tokenUsageTone(user)
                  return (
                    <tr key={user.id}>
                      <td>
                        {user.name}
                        <small>{user.email}</small>
                      </td>
                      <td>
                        <select
                          value={user.role}
                          disabled={pendingId === user.id || (isSelf && user.role === 'ADMIN')}
                          onChange={(event) => changeRole(user, event.target.value as User['role'])}
                        >
                          {roleOptions.map((option) => (
                            <option key={option.value} value={option.value}>{option.label}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <span className={`workspace-status ${user.is_active ? 'workspace-status-completed' : 'workspace-status-failed'}`}>
                          {user.is_active ? 'Ativo' : 'Inativo'}
                        </span>
                      </td>
                      <td>
                        {user.role === 'ADMIN' ? (
                          <span className="workspace-token-pill workspace-token-pill-exempt">Isento</span>
                        ) : (
                          <span className={`workspace-token-pill workspace-token-pill-${tone}`}>
                            {user.tokens_used_today.toLocaleString('pt-BR')}
                            {user.daily_token_limit_per_user > 0
                              ? ` / ${user.daily_token_limit_per_user.toLocaleString('pt-BR')}`
                              : ''}
                          </span>
                        )}
                      </td>
                      <td>{new Date(user.created_at).toLocaleDateString('pt-BR')}</td>
                      <td>
                        <button
                          type="button"
                          className="workspace-secondary-action"
                          disabled={pendingId === user.id || (isSelf && user.is_active)}
                          onClick={() => toggleStatus(user)}
                        >
                          {user.is_active ? 'Desativar' : 'Ativar'}
                        </button>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </div>
  )
}
