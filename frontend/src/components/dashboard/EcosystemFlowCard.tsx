export function EcosystemFlowCard() {
  return (
    <article className="workspace-panel workspace-panel-secondary">
      <div className="workspace-panel-heading">
        <div>
          <span className="workspace-card-kicker">ARQUITETURA</span>
          <h2>Como o ecossistema decide</h2>
        </div>
      </div>
      <p className="workspace-flow-caption">Solicitação → contexto → planejamento → agentes → validação</p>
      <div className="workspace-flow-diagram">
        <div className="workspace-flow-node">
          <span>Orientador</span>
        </div>
        <span className="workspace-flow-arrow" aria-hidden="true">→</span>
        <div className="workspace-flow-node workspace-flow-node-active">
          <span>Orquestrador</span>
        </div>
        <span className="workspace-flow-arrow" aria-hidden="true">→</span>
        <div className="workspace-flow-node">
          <span>Quality Gate</span>
        </div>
      </div>
    </article>
  )
}
