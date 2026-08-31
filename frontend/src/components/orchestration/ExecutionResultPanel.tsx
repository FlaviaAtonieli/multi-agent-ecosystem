import { OrchestrationExecutionResult } from '../../api/agentSkillsApi'

const confidenceLabels: Record<string, string> = { ALTO: 'Alta', MEDIO: 'Média', BAIXO: 'Baixa' }

const domainLabels: Record<string, string> = {
  codigo_legado: 'Código Legado',
  regras_negocio: 'Regras de Negócio',
  arquitetura_software: 'Arquitetura de Software',
  seguranca_informacao: 'Segurança da Informação',
}

function parseSynthesisByDomain(text: string): Array<{ domain: string; text: string }> {
  const matches = [...text.matchAll(/\[([a-z_]+)\]\s*/g)]
  if (matches.length === 0) return [{ domain: '', text }]

  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length
    return { domain: match[1], text: text.slice(start, end).trim() }
  })
}

export function ExecutionResultPanel({ execution }: { execution: OrchestrationExecutionResult }) {
  const { consolidated_response: consolidated, verdict, results } = execution
  const synthesisParts = parseSynthesisByDomain(consolidated.technical_synthesis)

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

      <div className="workspace-execution-block">
        <h4>Síntese consolidada</h4>
        <div className="workspace-synthesis-list">
          {synthesisParts.map((part, index) => (
            <div key={`${part.domain}-${index}`} className="workspace-synthesis-item">
              {part.domain && <span className="workspace-synthesis-domain">{domainLabels[part.domain] ?? part.domain}</span>}
              <p>{part.text}</p>
            </div>
          ))}
        </div>
      </div>

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
          {results.map((result, index) => (
            <article key={`${result.agente_emissor.nome}-${index}`} className="workspace-execution-skill-card">
              <header>
                <div>
                  <strong>{result.agente_emissor.nome}</strong>
                  <span className="workspace-skill-card-domain">{domainLabels[result.agente_emissor.dominio] ?? result.agente_emissor.dominio}</span>
                </div>
                <span
                  className={`workspace-confidence-pill workspace-confidence-${result.governanca.nivel_confianca.toLowerCase()}`}
                >
                  {confidenceLabels[result.governanca.nivel_confianca]}
                </span>
              </header>
              <p>{result.analise_estruturada.resumo_executivo}</p>

              {result.analise_estruturada.descobertas_tecnicas.length > 0 && (
                <div className="workspace-findings">
                  {result.analise_estruturada.descobertas_tecnicas.map((finding, findingIndex) => (
                    <div key={findingIndex} className="workspace-finding">
                      <strong>{finding.item_identificado}</strong>
                      <p>{finding.descricao_detalhada}</p>
                      {finding.trecho_referenciado && (
                        <pre className="workspace-code-block"><code>{finding.trecho_referenciado}</code></pre>
                      )}
                    </div>
                  ))}
                </div>
              )}

              <small className="workspace-skill-card-justification">{result.governanca.justificativa_confianca}</small>
            </article>
          ))}
        </div>
      </div>
    </div>
  )
}
