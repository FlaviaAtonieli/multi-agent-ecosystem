import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import type { User } from '../../api/authApi'
import { Brand } from '../Brand'
import '../../styles/workspace.css'

const principalNavigation = [
  { to: '/dashboard', label: 'Visão geral', symbol: '◫' },
  { to: '/requests/new', label: 'Nova solicitação', symbol: '+' },
  { to: '/orchestrations', label: 'Orquestrações', symbol: '◎' },
]

const ecosystemNavigation = [
  { to: '/agent-skills', label: 'Agent Skills', symbol: '◇' },
]

const roleLabels: Record<User['role'], string> = {
  USER: 'Usuário',
  TECHNICIAN: 'Usuário técnico',
  REVIEWER: 'Revisor',
  ADMIN: 'Administrador',
}

const AUDIT_ROLES: Array<User['role']> = ['REVIEWER', 'ADMIN']

export function AppShell() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const canViewAudit = user ? AUDIT_ROLES.includes(user.role) : false

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-brand"><Brand /></div>

        <nav className="workspace-nav" aria-label="Navegação principal">
          <span className="workspace-nav-label">PRINCIPAL</span>
          {principalNavigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `workspace-nav-link${isActive ? ' active' : ''}`}
            >
              <span aria-hidden="true">{item.symbol}</span>
              {item.label}
            </NavLink>
          ))}

          <div className="workspace-nav-divider" />
          <span className="workspace-nav-label">ECOSSISTEMA</span>
          {ecosystemNavigation.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `workspace-nav-link${isActive ? ' active' : ''}`}
            >
              <span aria-hidden="true">{item.symbol}</span>
              {item.label}
            </NavLink>
          ))}
          {canViewAudit ? (
            <NavLink to="/auditoria" className={({ isActive }) => `workspace-nav-link${isActive ? ' active' : ''}`}>
              <span aria-hidden="true">⌁</span> Auditoria
            </NavLink>
          ) : (
            <button className="workspace-nav-link workspace-nav-disabled" type="button" disabled title="Disponível para revisores e administradores">
              <span aria-hidden="true">⌁</span> Auditoria
            </button>
          )}
        </nav>

        <div className="workspace-sidebar-footer">
          <span className="workspace-live-dot" />
          <div>
            <strong>Ecossistema operacional</strong>
            <small>Base de orquestração v1</small>
          </div>
        </div>
      </aside>

      <div className="workspace-main">
        <header className="workspace-topbar">
          <div>
            <span className="workspace-breadcrumb">MULTI-AGENT ECOSYSTEM</span>
          </div>
          <div className="workspace-user">
            <div className="workspace-avatar" aria-hidden="true">
              {user?.name?.slice(0, 1).toUpperCase() ?? 'U'}
            </div>
            <div>
              <strong>{user?.name}</strong>
              <small>{user ? roleLabels[user.role] : 'Usuário técnico'}</small>
            </div>
            <button className="workspace-logout" type="button" onClick={handleLogout}>Sair</button>
          </div>
        </header>

        <main className="workspace-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
