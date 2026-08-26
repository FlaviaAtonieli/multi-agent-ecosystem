import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'

export function ProtectedRoute() {
  const { user, loading } = useAuth()
  if (loading) return <div className="page-loader">Preparando ambiente seguro…</div>
  return user ? <Outlet /> : <Navigate to="/login" replace />
}
