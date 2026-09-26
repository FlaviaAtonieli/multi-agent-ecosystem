import { FormEvent, useState } from 'react'
import { domainLabels } from './shared'

type FollowUpFormProps = {
  participatingDomains: string[]
  onAsk: (question: string, targetDomain: string | null) => Promise<void>
  submitting: boolean
  error: string
}

export function FollowUpForm({ participatingDomains, onAsk, submitting, error }: FollowUpFormProps) {
  const [question, setQuestion] = useState('')
  const [targetDomain, setTargetDomain] = useState('')

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    await onAsk(question, targetDomain || null)
    setQuestion('')
  }

  return (
    <form className="workspace-follow-up-form" onSubmit={handleSubmit}>
      <h4>Continuar a interação</h4>
      <label className="workspace-field">
        Pergunta de acompanhamento
        <textarea
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={3}
          minLength={5}
          required
          placeholder="Ainda tem dúvidas? Pergunte novamente com base no que já foi respondido..."
        />
      </label>
      <label className="workspace-field">
        Perguntar para
        <select value={targetDomain} onChange={(event) => setTargetDomain(event.target.value)}>
          <option value="">Todos os agentes envolvidos</option>
          {participatingDomains.map((domain) => (
            <option key={domain} value={domain}>{domainLabels[domain] ?? domain}</option>
          ))}
        </select>
      </label>
      {error && <div className="alert alert-error">{error}</div>}
      <button className="workspace-primary-action" type="submit" disabled={submitting}>
        {submitting ? 'Perguntando…' : 'Perguntar'}
      </button>
    </form>
  )
}
