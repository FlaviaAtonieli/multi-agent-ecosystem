import { FormEvent, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { authApi } from '../api/authApi'
import { ApiError } from '../api/http'
import { AgentNetworkHero } from '../components/AgentNetworkHero'

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get('token') ?? ''
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [done, setDone] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    if (password !== confirmation) {
      setError('As senhas não conferem.')
      return
    }
    setSubmitting(true)
    try {
      await authApi.resetPassword(token, password)
      setDone(true)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível redefinir a senha.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <AgentNetworkHero variant="login" />

      <section className="auth-panel">
        <div className="auth-card">
          <span className="card-kicker">Recuperar acesso</span>
          <h2>Criar nova senha</h2>

          {!token ? (
            <div className="alert alert-error" role="alert">
              Link incompleto. <Link to="/forgot-password">Peça um novo link</Link>.
            </div>
          ) : done ? (
            <div className="alert alert-success" role="status">
              Senha redefinida. Por segurança, todas as sessões abertas foram encerradas e o próximo login vai pedir
              o código enviado por e-mail. <Link to="/login">Entrar</Link>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="form-stack">
              <label>
                Nova senha
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="new-password"
                  required
                  minLength={12}
                />
                <small>Mínimo de 12 caracteres, com maiúscula, minúscula, número e caractere especial.</small>
              </label>
              <label>
                Confirmar nova senha
                <input
                  type="password"
                  value={confirmation}
                  onChange={(event) => setConfirmation(event.target.value)}
                  autoComplete="new-password"
                  required
                  minLength={12}
                />
              </label>

              {error && (
                <div className="alert alert-error" role="alert">
                  {error}
                </div>
              )}

              <button className="primary-button" type="submit" disabled={submitting}>
                {submitting ? 'Salvando…' : 'Salvar nova senha'}
              </button>
            </form>
          )}

          <p className="form-footer">
            <Link to="/login">Voltar ao login</Link>
          </p>
        </div>
      </section>
    </main>
  )
}
