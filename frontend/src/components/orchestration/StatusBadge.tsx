import { RequestStatus } from '../../api/orchestrationApi'

const statusLabels: Record<RequestStatus, string> = {
  RECEIVED: 'Recebida',
  AWAITING_CONTEXT: 'Aguardando contexto',
  QUALIFIED: 'Qualificada',
  PLANNING: 'Planejando',
  RUNNING: 'Em execução',
  VALIDATING: 'Quality Gate',
  COMPLETED: 'Concluída',
  REJECTED: 'Rejeitada',
  FAILED: 'Falha',
  CANCELLED: 'Cancelada',
}

export function StatusBadge({ status }: { status: RequestStatus }) {
  return <span className={`workspace-status workspace-status-${status.toLowerCase()}`}>{statusLabels[status]}</span>
}
