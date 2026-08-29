import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/http'
import { RequestStatus, TechnicalRequest, orchestrationApi } from '../api/orchestrationApi'
import { StatusBadge } from '../components/orchestration/StatusBadge'

type Bucket = 'ALL' | 'AWAITING' | 'RUNNING' | 'COMPLETED' | 'ERROR'

const bucketOf = (status: RequestStatus): Exclude<Bucket, 'ALL'> => {
  if (status === 'AWAITING_CONTEXT') return 'AWAITING'
  if (status === 'COMPLETED') return 'COMPLETED'
  if (status === 'FAILED' || status === 'CANCELLED' || status === 'REJECTED') return 'ERROR'
  return 'RUNNING'
}

const bucketLabels: Record<Bucket, string> = {
  ALL: 'Todas',
  AWAITING: 'Aguardando',
  RUNNING: 'Em execução',
  COMPLETED: 'Concluída',
  ERROR: 'Erro',
}

type SortOrder = 'recent' | 'oldest'

export function OrchestrationsPage() {
  const [requests, setRequests] = useState<TechnicalRequest[]>([])
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [bucket, setBucket] = useState<Bucket>('ALL')
  const [sortOrder, setSortOrder] = useState<SortOrder>('recent')

  useEffect(() => {
    orchestrationApi
      .listRequests()
      .then(setRequests)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar os fluxos.'))
  }, [])

  const counts = useMemo(() => {
    const result: Record<Bucket, number> = { ALL: requests.length, AWAITING: 0, RUNNING: 0, COMPLETED: 0, ERROR: 0 }
    for (const request of requests) result[bucketOf(request.status)] += 1
    return result
  }, [requests])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    const rows = requests.filter((request) => {
      const matchesBucket = bucket === 'ALL' || bucketOf(request.status) === bucket
      const matchesQuery =
        !query || request.title.toLowerCase().includes(query) || request.trace_id.toLowerCase().includes(query)
      return matchesBucket && matchesQuery
    })
    return rows.sort((a, b) => {
      const diff = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      return sortOrder === 'recent' ? -diff : diff
    })
  }, [requests, search, bucket, sortOrder])

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">ORQUESTRAÇÕES</span>
          <h1>Histórico de solicitações</h1>
          <p>Consulte estados, Trace IDs e o histórico de eventos de cada fluxo.</p>
        </div>
        <Link className="workspace-primary-action" to="/requests/new">+ Nova solicitação</Link>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="workspace-orchestrations-toolbar fade-up" style={{ animationDelay: '0.08s' }}>
        <input
          type="search"
          placeholder="Buscar por título ou Trace ID..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <div className="workspace-filter-chips" role="group" aria-label="Filtrar por status">
          {(Object.keys(bucketLabels) as Bucket[]).map((key) => (
            <button
              key={key}
              type="button"
              className={`workspace-filter-chip${bucket === key ? ' active' : ''}${key !== 'ALL' ? ` workspace-filter-chip-${key.toLowerCase()}` : ''}`}
              onClick={() => setBucket(key)}
            >
              {bucketLabels[key]} · {counts[key]}
            </button>
          ))}
        </div>

        <select value={sortOrder} onChange={(event) => setSortOrder(event.target.value as SortOrder)}>
          <option value="recent">Mais recentes</option>
          <option value="oldest">Mais antigas</option>
        </select>
      </div>

      <article className="workspace-panel">
        {filtered.length === 0 ? (
          <div className="workspace-empty">
            {requests.length === 0
              ? 'Nenhuma solicitação registrada ainda.'
              : 'Nenhuma solicitação corresponde ao filtro atual.'}
          </div>
        ) : (
          <div className="workspace-table-wrap">
            <table className="workspace-table workspace-table-orchestrations">
              <thead>
                <tr>
                  <th>Solicitação</th>
                  <th>Status</th>
                  <th>Trace ID</th>
                  <th>Data</th>
                  <th>Ações</th>
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
                    <td>
                      {request.status === 'AWAITING_CONTEXT' ? (
                        <Link className="workspace-action-outline-amber" to={`/orchestrations/${request.trace_id}`}>
                          Completar contexto
                        </Link>
                      ) : (
                        <Link className="workspace-action-link" to={`/orchestrations/${request.trace_id}`}>
                          Ver detalhes →
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </div>
  )
}
