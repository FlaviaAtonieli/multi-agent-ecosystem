import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { PublicRoute } from '../components/PublicRoute'
import { AgentSkillImportPage } from '../pages/AgentSkillImportPage'
import { AgentSkillsPage } from '../pages/AgentSkillsPage'
import { DashboardPage } from '../pages/DashboardPage'
import { LoginPage } from '../pages/LoginPage'
import { NewRequestPage } from '../pages/NewRequestPage'
import { OrchestrationPage } from '../pages/OrchestrationPage'
import { OrchestrationsPage } from '../pages/OrchestrationsPage'
import { RegisterPage } from '../pages/RegisterPage'

export function App() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/requests/new" element={<NewRequestPage />} />
          <Route path="/orchestrations" element={<OrchestrationsPage />} />
          <Route path="/orchestrations/:traceId" element={<OrchestrationPage />} />
          <Route path="/agent-skills" element={<AgentSkillsPage />} />
          <Route path="/agent-skills/import" element={<AgentSkillImportPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
