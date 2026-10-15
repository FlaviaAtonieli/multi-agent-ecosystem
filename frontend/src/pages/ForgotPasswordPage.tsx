import { FormEvent, useState } from 'react'
import { Link } from 'react-router-dom'
import { authApi } from '../api/authApi'
import { ApiError } from '../api/http'
import { AgentNetworkHero } from '../components/AgentNetworkHero'

export function ForgotPasswordPage() {
  const [email, setEmail] = useState('')
  const [sentMessage, setSentMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const result = await authApi.forgotPassword(email)
      setSentMessage(result.message)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível enviar o link agora.')
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
          <h2>Esqueci minha senha</h2>
          <p className="muted">Informe o e-mail da sua conta e enviaremos um link para criar uma nova senha.</p>

          {sentMessage ? (
            <div className="alert alert-success" role="status">
              {sentMessage} Confira também a caixa de spam.
            </div>
          ) : (
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

              {error && (
                <div className="alert alert-error" role="alert">
                  {error}
                </div>
              )}

              <button className="primary-button" type="submit" disabled={submitting}>
                {submitting ? 'Enviando…' : 'Enviar link'}
              </button>
            </form>
          )}

          <p className="form-footer">
            Lembrou a senha? <Link to="/login">Voltar ao login</Link>
          </p>
        </div>
      </section>
    </main>
  )
}
