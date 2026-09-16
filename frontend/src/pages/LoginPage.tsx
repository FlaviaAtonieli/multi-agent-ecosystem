import { FormEvent, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'
import { AgentNetworkHero } from '../components/AgentNetworkHero'
import { GitHubLoginButton } from '../components/GitHubLoginButton'

const GITHUB_ERROR_MESSAGES: Record<string, string> = {
  github_oauth_failed: 'Não foi possível concluir o login com GitHub. Tente novamente.',
  github_email_in_use: 'Já existe uma conta com este e-mail. Entre com e-mail e senha.',
  account_inactive: 'Esta conta está desativada.',
}

export function LoginPage() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [searchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const githubError = searchParams.get('error')
  const [error, setError] = useState(githubError ? GITHUB_ERROR_MESSAGES[githubError] ?? 'Não foi possível entrar com o GitHub.' : '')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      await login({ email, password })
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível entrar no sistema.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <AgentNetworkHero variant="login" />

      <section className="auth-panel">
        <div className="auth-card">
          <span className="card-kicker">Acesso ao ambiente</span>
          <h2>Boas-vindas</h2>
          <p className="muted">Entre com sua conta para acessar a base do ecossistema.</p>

          <form onSubmit={handleSubmit} className="form-stack">
            <label>
              E-mail
              <input
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="voce@empresa.com"
                required
              />
            </label>

            <label>
              Senha
              <input
                type="password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="Sua senha"
                required
              />
            </label>

            {error && (
              <div className="alert alert-error" role="alert">
                {error}
              </div>
            )}

            <button className="primary-button" type="submit" disabled={submitting}>
              {submitting ? 'Validando acesso…' : 'Entrar'}
            </button>
          </form>

          <div className="auth-divider">ou</div>
          <GitHubLoginButton />

          <p className="form-footer">
            Ainda não possui conta? <Link to="/register">Criar conta</Link>
          </p>
        </div>
      </section>
    </main>
  )
}
