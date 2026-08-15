import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { Brand } from '../Brand'
import '../../styles/workspace.css'

const navigation = [
  { to: '/dashboard', label: 'Visão geral', symbol: '◫' },
  { to: '/requests/new', label: 'Nova solicitação', symbol: '+' },
  { to: '/orchestrations', label: 'Orquestrações', symbol: '◎' },
]

export function AppShell() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  async function handleLogout() {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <div className="workspace-brand"><Brand /></div>

        <nav className="workspace-nav" aria-label="Navegação principal">
          {navigation.map((item) => (
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
          <button className="workspace-nav-link workspace-nav-disabled" type="button" disabled>
            <span aria-hidden="true">◇</span> Agent Skills
          </button>
          <button className="workspace-nav-link workspace-nav-disabled" type="button" disabled>
            <span aria-hidden="true">⌁</span> Auditoria
          </button>
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
              <small>{user?.role === 'ADMIN' ? 'Administrador' : 'Usuário técnico'}</small>
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
