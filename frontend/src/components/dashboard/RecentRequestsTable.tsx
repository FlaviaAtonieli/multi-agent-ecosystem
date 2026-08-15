import { Link } from 'react-router-dom'
import { TechnicalRequest } from '../../api/orchestrationApi'
import { StatusBadge } from '../orchestration/StatusBadge'

export function RecentRequestsTable({ requests }: { requests: TechnicalRequest[] }) {
  if (!requests.length) {
    return <div className="workspace-empty">Nenhuma solicitação registrada ainda.</div>
  }

  return (
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
          {requests.map((request) => (
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
  )
}
