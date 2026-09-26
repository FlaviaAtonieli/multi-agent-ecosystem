import { Link } from 'react-router-dom'
import { TechnicalRequest } from '../../api/orchestrationApi'

export function ActionBanner({ requests }: { requests: TechnicalRequest[] }) {
  const pending = requests
    .filter((request) => request.status === 'AWAITING_CONTEXT')
    .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())

  if (!pending.length) return null

  const oldest = pending[0]
  const destination = `/orchestrations/${oldest.trace_id}`

  return (
    <div className="workspace-action-banner">
      <div>
        <span className="workspace-action-banner-icon" aria-hidden="true">!</span>
        <div>
          <strong>
            {pending.length} solicitação{pending.length > 1 ? 'ões' : ''} aguardando complementação
          </strong>
          <p>&ldquo;{oldest.title}&rdquo; precisa de mais detalhes técnicos antes de seguir para o Orientador de Interação.</p>
        </div>
      </div>
      <Link className="workspace-action-banner-button" to={destination}>Completar agora →</Link>
    </div>
  )
}
