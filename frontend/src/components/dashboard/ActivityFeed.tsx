import { OrchestrationEvent } from '../../api/orchestrationApi'

export function ActivityFeed({ events }: { events: OrchestrationEvent[] }) {
  if (!events.length) {
    return <div className="workspace-empty">Os eventos das orquestrações aparecerão aqui.</div>
  }

  return (
    <div className="workspace-activity-list">
      {events.map((event) => (
        <article key={event.id} className="workspace-activity-item">
          <span className="workspace-activity-dot" />
          <div>
            <strong>{event.title}</strong>
            <p>{event.message}</p>
            <small>{event.actor} · {new Date(event.created_at).toLocaleString('pt-BR')}</small>
          </div>
        </article>
      ))}
    </div>
  )
}
