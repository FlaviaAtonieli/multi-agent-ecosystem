import { FormEvent, useEffect, useState } from 'react'
import { domainLabels, formatElapsed } from './shared'

type FollowUpFormProps = {
  participatingDomains: string[]
  onAsk: (question: string, targetDomain: string | null) => Promise<void>
  submitting: boolean
  pendingSince: string | null
  error: string
}

function PendingNotice({ since }: { since: string }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const elapsedSeconds = Math.max(0, Math.floor((now - new Date(since).getTime()) / 1000))
  return (
    <p className="workspace-thinking-estimate" role="status">
      <strong>Os agentes estão respondendo.</strong>{' '}
      <span role="timer" aria-live="off">{formatElapsed(elapsedSeconds)}</span>. Pode sair desta página: a resposta fica salva.
    </p>
  )
}

export function FollowUpForm({ participatingDomains, onAsk, submitting, pendingSince, error }: FollowUpFormProps) {
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
      {pendingSince && <PendingNotice since={pendingSince} />}
      {error && <div className="alert alert-error">{error}</div>}
      <button className="workspace-primary-action" type="submit" disabled={submitting || Boolean(pendingSince)}>
        {submitting || pendingSince ? 'Perguntando…' : 'Perguntar'}
      </button>
    </form>
  )
}
