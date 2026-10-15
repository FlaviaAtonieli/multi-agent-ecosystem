import { useState } from 'react'
import { ApiError } from '../../api/http'
import { orchestrationApi } from '../../api/orchestrationApi'

type Props = {
  requestId: string
  onReviewed: (decision: 'approve' | 'reject') => void
}

/** Revisão humana (RF11): o Conselheiro sinalizou o resultado e quem abriu a
 * solicitação decide se aceita a resposta ou a rejeita, com justificativa. */
export function HumanReviewPanel({ requestId, onReviewed }: Props) {
  const [notes, setNotes] = useState('')
  const [pending, setPending] = useState<'approve' | 'reject' | null>(null)
  const [error, setError] = useState('')

  async function decide(decision: 'approve' | 'reject') {
    if (decision === 'reject' && !notes.trim()) {
      setError('Explique o motivo da rejeição — ele fica registrado na linha do tempo.')
      return
    }
    setPending(decision)
    setError('')
    try {
      await orchestrationApi.review(requestId, decision, notes.trim() || null)
      onReviewed(decision)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível registrar a revisão.')
    } finally {
      setPending(null)
    }
  }

  return (
    <article className="workspace-panel workspace-review-panel">
      <div className="workspace-panel-heading">
        <div>
          <span className="workspace-card-kicker">REVISÃO HUMANA</span>
          <h2>Esta resposta precisa da sua avaliação</h2>
        </div>
      </div>
      <p className="workspace-review-hint">
        O Conselheiro não aprovou o resultado automaticamente (por exemplo, por confiança baixa ou pouca evidência).
        Leia a resposta acima e decida se ela pode ser usada.
      </p>
      <label className="workspace-field">
        Observações
        <textarea
          value={notes}
          onChange={(event) => setNotes(event.target.value)}
          rows={4}
          maxLength={2000}
          placeholder="Opcional ao aprovar, obrigatório ao rejeitar. Ex.: 'Faltou evidência sobre o módulo de faturamento.'"
        />
      </label>
      {error && <div className="alert alert-error">{error}</div>}
      <div className="workspace-review-actions">
        <button
          type="button"
          className="workspace-secondary-action"
          disabled={pending !== null}
          onClick={() => decide('reject')}
        >
          {pending === 'reject' ? 'Rejeitando…' : 'Rejeitar resposta'}
        </button>
        <button
          type="button"
          className="workspace-primary-action"
          disabled={pending !== null}
          onClick={() => decide('approve')}
        >
          {pending === 'approve' ? 'Aprovando…' : 'Aprovar resposta'}
        </button>
      </div>
    </article>
  )
}
