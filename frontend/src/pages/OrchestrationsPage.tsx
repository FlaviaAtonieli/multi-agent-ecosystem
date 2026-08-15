import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/http'
import { TechnicalRequest, orchestrationApi } from '../api/orchestrationApi'
import { RecentRequestsTable } from '../components/dashboard/RecentRequestsTable'

export function OrchestrationsPage() {
  const [requests, setRequests] = useState<TechnicalRequest[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    orchestrationApi
      .listRequests()
      .then(setRequests)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar os fluxos.'))
  }, [])

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading">
        <div>
          <span className="workspace-eyebrow">ORQUESTRAÇÕES</span>
          <h1>Histórico de solicitações</h1>
          <p>Consulte estados, Trace IDs e o histórico de eventos de cada fluxo.</p>
        </div>
        <Link className="workspace-primary-action" to="/requests/new">+ Nova solicitação</Link>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <article className="workspace-panel">
        <RecentRequestsTable requests={requests} />
      </article>
    </div>
  )
}
