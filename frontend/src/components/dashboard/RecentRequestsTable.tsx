import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { RequestStatus, TechnicalRequest } from '../../api/orchestrationApi'
import { StatusBadge } from '../orchestration/StatusBadge'

const statusOptions: Array<{ value: RequestStatus | 'ALL'; label: string }> = [
  { value: 'ALL', label: 'Todos os status' },
  { value: 'RECEIVED', label: 'Recebida' },
  { value: 'AWAITING_CONTEXT', label: 'Aguardando contexto' },
  { value: 'QUALIFIED', label: 'Qualificada' },
  { value: 'PLANNING', label: 'Planejando' },
  { value: 'RUNNING', label: 'Em execução' },
  { value: 'VALIDATING', label: 'Quality Gate' },
  { value: 'COMPLETED', label: 'Concluída' },
  { value: 'REJECTED', label: 'Rejeitada' },
  { value: 'FAILED', label: 'Falha' },
  { value: 'CANCELLED', label: 'Cancelada' },
]

export function RecentRequestsTable({ requests, showToolbar = false }: { requests: TechnicalRequest[]; showToolbar?: boolean }) {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<RequestStatus | 'ALL'>('ALL')

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return requests.filter((request) => {
      const matchesStatus = status === 'ALL' || request.status === status
      const matchesQuery =
        !query || request.title.toLowerCase().includes(query) || request.trace_id.toLowerCase().includes(query)
      return matchesStatus && matchesQuery
    })
  }, [requests, search, status])

  return (
    <div>
      {showToolbar && (
        <div className="workspace-table-toolbar">
          <input
            type="search"
            placeholder="Buscar por título ou Trace ID..."
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
          <select value={status} onChange={(event) => setStatus(event.target.value as RequestStatus | 'ALL')}>
            {statusOptions.map((option) => (
              <option key={option.value} value={option.value}>{option.label}</option>
            ))}
          </select>
        </div>
      )}

      {filtered.length === 0 ? (
        <div className="workspace-empty">
          {requests.length === 0
            ? 'Novas solicitações registradas aparecerão nesta lista.'
            : 'Nenhuma solicitação corresponde ao filtro atual.'}
        </div>
      ) : (
        <div className="workspace-table-wrap">
          <table className="workspace-table">
            <thead>
              <tr>
                <th>Solicitação</th>
                <th>Status</th>
                <th>Trace ID</th>
                <th>Data</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((request) => (
                <tr key={request.id}>
                  <td>
                    <Link to={`/orchestrations/${request.trace_id}`}>{request.title}</Link>
                    <small>{request.objective}</small>
                  </td>
                  <td><StatusBadge status={request.status} /></td>
                  <td><code>{request.trace_id}</code></td>
                  <td>{new Date(request.created_at).toLocaleString('pt-BR')}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
