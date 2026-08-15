export function EcosystemOverview() {
  return (
    <div className="workspace-ecosystem" aria-label="Representação do ecossistema de agentes">
      <div className="workspace-ecosystem-line line-a" />
      <div className="workspace-ecosystem-line line-b" />
      <div className="workspace-ecosystem-line line-c" />
      <span className="workspace-agent-node node-orchestrator">Orquestrador</span>
      <span className="workspace-agent-node node-guide">Orientador</span>
      <span className="workspace-agent-node node-legacy">Legado</span>
      <span className="workspace-agent-node node-business">Negócio</span>
      <span className="workspace-agent-node node-quality">Quality Gate</span>
      <div className="workspace-ecosystem-caption">
        <strong>Fundação do fluxo</strong>
        <small>Solicitação → contexto → planejamento → agentes → validação</small>
      </div>
    </div>
  )
}
