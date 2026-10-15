import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { authApi } from '../api/authApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'
import { AgentNetworkHero } from '../components/AgentNetworkHero'
import { GitHubLoginButton } from '../components/GitHubLoginButton'
import { GoogleLoginButton } from '../components/GoogleLoginButton'

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  github_oauth_failed: 'Não foi possível concluir o login com GitHub. Tente novamente.',
  github_email_in_use: 'Já existe uma conta com este e-mail. Entre com e-mail e senha.',
  google_oauth_failed: 'Não foi possível concluir o login com Google. Tente novamente.',
  google_email_in_use: 'Já existe uma conta com este e-mail. Entre com e-mail e senha.',
  account_inactive: 'Esta conta está desativada.',
  login_code_failed: 'Não foi possível enviar o código de acesso por e-mail. Tente novamente.',
}

export function LoginPage() {
  const navigate = useNavigate()
  const { login, verifyLoginCode } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const oauthError = searchParams.get('error')
  const [error, setError] = useState(oauthError ? OAUTH_ERROR_MESSAGES[oauthError] ?? 'Não foi possível entrar.' : '')
  const [notice, setNotice] = useState('')
  const [submitting, setSubmitting] = useState(false)
  // Preenchido quando o login precisa do código enviado por e-mail (navegador novo).
  const [emailHint, setEmailHint] = useState<string | null>(null)
  const [code, setCode] = useState('')

  // Volta do GitHub/Google com ?verify=1: o backend já enviou o código.
  useEffect(() => {
    if (searchParams.get('verify') !== '1') return
    authApi
      .loginChallenge()
      .then((challenge) => setEmailHint(challenge.email_hint))
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Entre novamente.'))
    setSearchParams({}, { replace: true })
  }, [searchParams, setSearchParams])

  function backToPassword(message = '') {
    setEmailHint(null)
    setCode('')
    setNotice('')
    setError(message)
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)

    try {
      const challenge = await login({ email, password })
      if (challenge) {
        setEmailHint(challenge.email_hint)
        return
      }
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível entrar no sistema.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setNotice('')
    setSubmitting(true)

    try {
      await verifyLoginCode(code)
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 410) {
        backToPassword(caught.message)
      } else {
        setError(caught instanceof ApiError ? caught.message : 'Não foi possível validar o código.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function handleResend() {
    setError('')
    setNotice('')
    try {
      await authApi.resendLoginCode()
      setNotice('Enviamos um novo código.')
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 410) {
        backToPassword(caught.message)
      } else {
        setError(caught instanceof ApiError ? caught.message : 'Não foi possível reenviar o código.')
      }
    }
  }

  return (
    <main className="auth-page">
      <AgentNetworkHero variant="login" />

      <section className="auth-panel">
        <div className="auth-card">
          {emailHint ? (
            <>
              <span className="card-kicker">Verificação em duas etapas</span>
              <h2>Confirme que é você</h2>
              <p className="muted">
                Este navegador ainda não é conhecido. Enviamos um código de 6 dígitos para <strong>{emailHint}</strong>.
              </p>

              <form onSubmit={handleVerify} className="form-stack">
                <label>
                  Código de acesso
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    pattern="\d{6}"
                    maxLength={6}
                    value={code}
                    onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                    placeholder="000000"
                    autoFocus
                    required
                  />
                </label>

                {error && (
                  <div className="alert alert-error" role="alert">
                    {error}
                  </div>
                )}
                {notice && (
                  <div className="alert alert-success" role="status">
                    {notice}
                  </div>
                )}

                <button className="primary-button" type="submit" disabled={submitting || code.length !== 6}>
                  {submitting ? 'Validando código…' : 'Confirmar e entrar'}
                </button>
              </form>

              <p className="form-footer">
                Não recebeu?{' '}
                <button type="button" className="link-button" onClick={handleResend}>
                  Reenviar código
                </button>{' '}
                ·{' '}
                <button type="button" className="link-button" onClick={() => backToPassword()}>
                  Voltar
                </button>
              </p>
            </>
          ) : (
            <>
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
                  <span className="label-row">
                    Senha
                    <Link to="/forgot-password" className="label-link">
                      Esqueci minha senha
                    </Link>
                  </span>
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
              <GoogleLoginButton />

              <p className="form-footer">
                Ainda não possui conta? <Link to="/register">Criar conta</Link>
              </p>
            </>
          )}
        </div>
      </section>
    </main>
  )
}
