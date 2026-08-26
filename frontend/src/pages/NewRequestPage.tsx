import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { orchestrationApi } from '../api/orchestrationApi'

export function NewRequestPage() {
  const navigate = useNavigate()
  const [title, setTitle] = useState('')
  const [problem, setProblem] = useState('')
  const [objective, setObjective] = useState('')
  const [context, setContext] = useState('')
  const [restrictions, setRestrictions] = useState('Não executar alterações automaticamente')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      const created = await orchestrationApi.createRequest({
        title,
        problem,
        objective,
        context: context.trim() || null,
        restrictions: restrictions
          .split(/\n|,/)
          .map((item) => item.trim())
          .filter(Boolean),
      })
      navigate(`/orchestrations/${created.trace_id}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível criar a solicitação.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="workspace-page workspace-page-narrow">
      <section className="workspace-page-heading">
        <div>
          <span className="workspace-eyebrow">NOVA SOLICITAÇÃO</span>
          <h1>Qualifique uma demanda técnica</h1>
          <p>Esses dados formarão o contexto inicial entregue ao Orientador de Interação.</p>
        </div>
      </section>

      <form className="workspace-form-panel" onSubmit={handleSubmit}>
        <div className="workspace-form-grid">
          <label className="workspace-field workspace-field-full">
            Título
            <input value={title} onChange={(event) => setTitle(event.target.value)} minLength={5} maxLength={160} required />
            <small>Uma identificação curta para o fluxo.</small>
          </label>

          <label className="workspace-field workspace-field-full">
            Problema a ser analisado
            <textarea value={problem} onChange={(event) => setProblem(event.target.value)} rows={5} minLength={10} required />
            <small>Descreva o comportamento atual, a divergência ou a dúvida técnica.</small>
          </label>

          <label className="workspace-field workspace-field-full">
            Objetivo da análise
            <textarea value={objective} onChange={(event) => setObjective(event.target.value)} rows={3} minLength={5} required />
            <small>Informe qual resposta ou resultado você espera obter.</small>
          </label>

          <label className="workspace-field workspace-field-full">
            Contexto técnico
            <textarea value={context} onChange={(event) => setContext(event.target.value)} rows={7} />
            <small>
              Inclua módulos, tecnologias, artefatos, dependências e comportamento esperado. Caso seja insuficiente,
              a solicitação ficará aguardando complementação.
            </small>
          </label>

          <label className="workspace-field workspace-field-full">
            Restrições
            <textarea value={restrictions} onChange={(event) => setRestrictions(event.target.value)} rows={3} />
            <small>Separe restrições por linha ou vírgula.</small>
          </label>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="workspace-form-actions">
          <button type="button" className="workspace-secondary-action" onClick={() => navigate(-1)}>Cancelar</button>
          <button type="submit" className="workspace-primary-action" disabled={submitting}>
            {submitting ? 'Registrando…' : 'Registrar e gerar Trace ID'}
          </button>
        </div>
      </form>
    </div>
  )
}
