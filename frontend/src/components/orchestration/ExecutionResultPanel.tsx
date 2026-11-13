import { ReactNode, useState } from 'react'
import { OrchestrationExecutionResult } from '../../api/agentSkillsApi'
import { confidenceLabels, SkillResultCard, SynthesisByDomain } from './shared'

type Props = {
  execution: OrchestrationExecutionResult
  // Arquivos e ZIP gerados pela orquestração, entre o resumo e as respostas dos agentes.
  material?: ReactNode
  // Avaliação de cada resposta, na ordem de `execution.results`.
  feedbackFor?: (index: number) => ReactNode
}

// A resposta final em três partes: o resumo para decidir rápido, o material
// entregue (arquivos) e, fechada por padrão, a resposta completa de cada agente.
export function ExecutionResultPanel({ execution, material, feedbackFor }: Props) {
  const { consolidated_response: consolidated, verdict, results } = execution
  const [openCards, setOpenCards] = useState<Set<number>>(new Set())
  const allOpen = results.length > 0 && openCards.size === results.length

  function toggleCard(index: number) {
    setOpenCards((current) => {
      const next = new Set(current)
      if (next.has(index)) next.delete(index)
      else next.add(index)
      return next
    })
  }

  function toggleAll() {
    setOpenCards(allOpen ? new Set() : new Set(results.map((_, index) => index)))
  }

  return (
    <div className="workspace-execution">
      <section className="workspace-result-section" aria-labelledby="result-summary-title">
        <h3 id="result-summary-title">Resumo</h3>
        <div className="workspace-execution-summary">
          <span className={`workspace-status ${verdict.approved ? 'workspace-status-completed' : 'workspace-status-validating'}`}>
            {verdict.approved ? 'Aprovado pelo Quality Gate' : 'Requer revisão humana'}
          </span>
          <span className={`workspace-confidence-pill workspace-confidence-${consolidated.overall_confidence_level.toLowerCase()}`}>
            Confiança geral: {confidenceLabels[consolidated.overall_confidence_level]}
          </span>
          <span className="workspace-result-facts">
            {results.length} {results.length === 1 ? 'agente respondeu' : 'agentes responderam'}
          </span>
        </div>

        <SynthesisByDomain domains={results.map((result) => result.agente_emissor.dominio)} text={consolidated.technical_synthesis} />

        {(consolidated.risks.length > 0 || consolidated.recommendations.length > 0) && (
          <div className="workspace-result-lists">
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
          </div>
        )}
      </section>

      {material}

      <section className="workspace-result-section" aria-labelledby="result-agents-title">
        <div className="workspace-result-section-heading">
          <h3 id="result-agents-title">Resposta de cada agente ({results.length})</h3>
          {results.length > 1 && (
            <button type="button" className="workspace-code-block-action" onClick={toggleAll}>
              {allOpen ? 'Recolher todos' : 'Expandir todos'}
            </button>
          )}
        </div>
        <div className="workspace-execution-skills">
          {results.map((result, index) => (
            <SkillResultCard
              key={`${result.agente_emissor.nome}-${index}`}
              result={result}
              collapsible
              open={openCards.has(index)}
              onToggle={() => toggleCard(index)}
              footer={feedbackFor?.(index)}
            />
          ))}
        </div>
      </section>
    </div>
  )
}
