import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '../components/layout/AppShell'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { PublicRoute } from '../components/PublicRoute'
import { AccountPage } from '../pages/AccountPage'
import { AgentSkillCreatePage } from '../pages/AgentSkillCreatePage'
import { AgentSkillImportPage } from '../pages/AgentSkillImportPage'
import { AgentSkillsPage } from '../pages/AgentSkillsPage'
import { AuditoriaPage } from '../pages/AuditoriaPage'
import { ClansPage } from '../pages/ClansPage'
import { DashboardPage } from '../pages/DashboardPage'
import { ForgotPasswordPage } from '../pages/ForgotPasswordPage'
import { LoginPage } from '../pages/LoginPage'
import { NewRequestPage } from '../pages/NewRequestPage'
import { OrchestrationPage } from '../pages/OrchestrationPage'
import { OrchestrationsPage } from '../pages/OrchestrationsPage'
import { RegisterPage } from '../pages/RegisterPage'
import { ResetPasswordPage } from '../pages/ResetPasswordPage'

export function App() {
  return (
    <Routes>
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      </Route>
      {/* Fora do PublicRoute: o link do e-mail precisa abrir mesmo com alguém logado neste navegador. */}
      <Route path="/reset-password" element={<ResetPasswordPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppShell />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/requests/new" element={<NewRequestPage />} />
          <Route path="/orchestrations" element={<OrchestrationsPage />} />
          <Route path="/orchestrations/:traceId" element={<OrchestrationPage />} />
          <Route path="/agent-skills" element={<AgentSkillsPage />} />
          <Route path="/agent-skills/new" element={<AgentSkillCreatePage />} />
          <Route path="/agent-skills/import" element={<AgentSkillImportPage />} />
          <Route path="/agent-skills/:skillId/edit" element={<AgentSkillCreatePage />} />
          <Route path="/clans" element={<ClansPage />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/auditoria" element={<AuditoriaPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
