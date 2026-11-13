import { FormEvent, useId, useState } from 'react'
import { ApiError } from '../../api/http'
import { AgentResponseFeedback, FeedbackReason, orchestrationApi } from '../../api/orchestrationApi'

export const feedbackReasonLabels: Record<FeedbackReason, string> = {
  INCORRETA: 'Incorreta',
  INCOMPLETA: 'Incompleta',
  FORA_DO_ASSUNTO: 'Fora do assunto',
  SEM_EVIDENCIA: 'Sem evidência',
}

type Props = {
  traceId: string
  invocationId: string
  agentName: string
  initial: AgentResponseFeedback | null
}

// Avaliação da resposta de um agente. Só registra: não muda a resposta nem a decisão
// do Quality Gate. Não útil exige um motivo, para a métrica dizer o que falhou.
export function AgentFeedback({ traceId, invocationId, agentName, initial }: Props) {
  const [feedback, setFeedback] = useState<AgentResponseFeedback | null>(initial ?? null)
  const [askingReason, setAskingReason] = useState(false)
  const [reason, setReason] = useState<FeedbackReason | null>(initial?.reason ?? null)
  const [comment, setComment] = useState(initial?.comment ?? '')
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const id = useId()

  async function run(action: () => Promise<AgentResponseFeedback | null>) {
    setSaving(true)
    setError('')
    setMessage('')
    try {
      const result = await action()
      setFeedback(result)
      setAskingReason(false)
      setMessage(result ? 'Avaliação salva.' : 'Avaliação removida.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível salvar a avaliação.')
    } finally {
      setSaving(false)
    }
  }

  function toggleUseful() {
    if (feedback?.useful) {
      run(async () => {
        await orchestrationApi.removeSkillResultRating(traceId, invocationId)
        return null
      })
      return
    }
    run(() => orchestrationApi.rateSkillResult(traceId, invocationId, { useful: true }))
  }

  function saveNotUseful(event: FormEvent) {
    event.preventDefault()
    if (!reason) return
    const trimmed = comment.trim()
    run(() =>
      orchestrationApi.rateSkillResult(traceId, invocationId, {
        useful: false,
        reason,
        ...(trimmed ? { comment: trimmed } : {}),
      }),
    )
  }

  const notUseful = feedback !== null && !feedback.useful

  return (
    <div className="workspace-agent-feedback">
      <div className="workspace-agent-feedback-row" role="group" aria-label={`Avaliar a resposta de ${agentName}`}>
        <span className="workspace-agent-feedback-question">Esta resposta foi útil?</span>
        <button
          type="button"
          className="workspace-agent-feedback-button"
          aria-pressed={feedback?.useful === true}
          disabled={saving}
          onClick={toggleUseful}
        >
          <span aria-hidden="true">👍 </span>Útil
        </button>
        <button
          type="button"
          className="workspace-agent-feedback-button"
          aria-pressed={notUseful}
          aria-expanded={askingReason}
          disabled={saving}
          onClick={() => setAskingReason((value) => !value)}
        >
          <span aria-hidden="true">👎 </span>Não útil
        </button>
      </div>

      {notUseful && feedback.reason && !askingReason && (
        <p className="workspace-agent-feedback-saved">Motivo: {feedbackReasonLabels[feedback.reason]}</p>
      )}

      {askingReason && (
        <form className="workspace-agent-feedback-form" onSubmit={saveNotUseful}>
          <fieldset>
            <legend>Por que não foi útil?</legend>
            {(Object.keys(feedbackReasonLabels) as FeedbackReason[]).map((option) => (
              <label key={option} className="workspace-agent-feedback-reason">
                <input
                  type="radio"
                  name={`${id}-reason`}
                  value={option}
                  checked={reason === option}
                  onChange={() => setReason(option)}
                />
                {feedbackReasonLabels[option]}
              </label>
            ))}
          </fieldset>
          <label htmlFor={`${id}-comment`}>Comentário (opcional)</label>
          <textarea
            id={`${id}-comment`}
            value={comment}
            maxLength={1000}
            rows={2}
            onChange={(event) => setComment(event.target.value)}
          />
          <div className="workspace-agent-feedback-actions">
            <button type="button" className="workspace-secondary-action" onClick={() => setAskingReason(false)}>
              Cancelar
            </button>
            <button type="submit" className="workspace-primary-action" disabled={!reason || saving}>
              Salvar avaliação
            </button>
          </div>
        </form>
      )}

      {message && (
        <p role="status" className="workspace-agent-feedback-status">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}
    </div>
  )
}
