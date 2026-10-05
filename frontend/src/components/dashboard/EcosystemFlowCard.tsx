import { CollapsibleSection } from '../shared/CollapsibleSection'

export function EcosystemFlowCard() {
  return (
    <CollapsibleSection title="Como o ecossistema decide" defaultOpen={false}>
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
    </CollapsibleSection>
  )
}
