import { FormEvent, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'
import { AgentNetworkHero } from '../components/AgentNetworkHero'

export function RegisterPage() {
  const navigate = useNavigate()
  const { register } = useAuth()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError('')

    if (password !== confirmation) {
      setError('As senhas informadas não coincidem.')
      return
    }

    setSubmitting(true)

    try {
      await register({ name, email, password })
      navigate('/dashboard', { replace: true })
    } catch (caught) {
      if (caught instanceof ApiError) {
        const fieldMessage = caught.details?.map((item) => item.message).join(' ')
        setError(fieldMessage || caught.message)
      } else {
        setError('Não foi possível criar sua conta.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="auth-page">
      <AgentNetworkHero variant="register" />

      <section className="auth-panel">
        <div className="auth-card register-card">
          <span className="card-kicker">Cadastro seguro</span>
          <h2>Criar conta</h2>
          <p className="muted">Use uma senha com pelo menos 12 caracteres.</p>

          <form onSubmit={handleSubmit} className="form-stack">
            <label>
              Nome completo
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                autoComplete="name"
                required
              />
            </label>

            <label>
              E-mail
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="email"
                required
              />
            </label>

            <label>
              Senha
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="new-password"
                required
                minLength={12}
              />
              <small>Maiúscula, minúscula, número e caractere especial.</small>
            </label>

            <label>
              Confirmar senha
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
              {submitting ? 'Criando conta…' : 'Criar conta'}
            </button>
          </form>

          <p className="form-footer">
            Já possui conta? <Link to="/login">Voltar ao login</Link>
          </p>
        </div>
      </section>
    </main>
  )
}
