import { OrchestrationEvent } from '../../api/orchestrationApi'

const actorLabels: Record<string, string> = {
  USER: 'Usuário',
  INTERACTION_GUIDE: 'Orientador de Interação',
  ORCHESTRATOR: 'Orquestrador',
  ADVISORY_AGENT: 'Agent Skill',
  REVIEWER: 'Revisor',
  RETRIEVAL_AGENT: 'RAG',
  TECHNICAL_PLANNER: 'Planejador Técnico',
}

const actorTones: Record<string, string> = {
  USER: 'violet',
  INTERACTION_GUIDE: 'amber',
  ORCHESTRATOR: 'cyan',
  ADVISORY_AGENT: 'sky',
  REVIEWER: 'sky',
  RETRIEVAL_AGENT: 'sky',
  TECHNICAL_PLANNER: 'sky',
}

export function ActivityFeed({ events }: { events: OrchestrationEvent[] }) {
  if (!events.length) {
    return <div className="workspace-empty">Os eventos das orquestrações aparecerão aqui.</div>
  }

  const recent = events.slice(0, 4)

  return (
    <div className="workspace-mini-timeline">
      {recent.map((event) => (
        <article key={event.id} className="workspace-mini-timeline-item">
          <span className={`workspace-mini-timeline-dot workspace-mini-timeline-dot-${actorTones[event.actor] ?? 'sky'}`} aria-hidden="true" />
          <div>
            <strong>{event.title}</strong>
            <p>{event.message}</p>
            <small>{(actorLabels[event.actor] ?? event.actor).toUpperCase()} · {new Date(event.created_at).toLocaleString('pt-BR')}</small>
          </div>
        </article>
      ))}
    </div>
  )
}
