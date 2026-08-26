import { OrchestrationExecutionResult } from '../../api/agentSkillsApi'

const confidenceLabels: Record<string, string> = { ALTO: 'Alta', MEDIO: 'Média', BAIXO: 'Baixa' }

export function ExecutionResultPanel({ execution }: { execution: OrchestrationExecutionResult }) {
  const { consolidated_response: consolidated, verdict, results } = execution

  return (
    <div className="workspace-execution">
      <div className="workspace-execution-summary">
        <span className={`workspace-status ${verdict.approved ? 'workspace-status-completed' : 'workspace-status-validating'}`}>
          {verdict.approved ? 'Aprovado pelo Quality Gate' : 'Requer revisão humana'}
        </span>
        <span className={`workspace-confidence-pill workspace-confidence-${consolidated.overall_confidence_level.toLowerCase()}`}>
          Confiança geral: {confidenceLabels[consolidated.overall_confidence_level]}
        </span>
      </div>

      <p className="workspace-execution-synthesis">{consolidated.technical_synthesis}</p>

      {consolidated.risks.length > 0 && (
        <div className="workspace-execution-block">
          <h4>Riscos mapeados</h4>
          <ul>
            {consolidated.risks.map((risk) => (
              <li key={risk}>{risk}</li>
            ))}
          </ul>
        </div>
      )}

      {consolidated.recommendations.length > 0 && (
        <div className="workspace-execution-block">
          <h4>Recomendações</h4>
          <ul>
            {consolidated.recommendations.map((recommendation) => (
              <li key={recommendation}>{recommendation}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="workspace-execution-block">
        <h4>Respostas por Agent Skill ({results.length})</h4>
        <div className="workspace-execution-skills">
          {results.map((result) => (
            <article key={result.agente_emissor.nome} className="workspace-execution-skill-card">
              <header>
                <strong>{result.agente_emissor.nome}</strong>
                <span
                  className={`workspace-confidence-pill workspace-confidence-${result.governanca.nivel_confianca.toLowerCase()}`}
                >
                  {confidenceLabels[result.governanca.nivel_confianca]}
                </span>
              </header>
              <p>{result.analise_estruturada.resumo_executivo}</p>
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
