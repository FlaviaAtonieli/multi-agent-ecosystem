import { SkillToolResult } from '../../api/agentSkillsApi'

export const confidenceLabels: Record<string, string> = { ALTO: 'Alta', MEDIO: 'Média', BAIXO: 'Baixa' }

export const domainLabels: Record<string, string> = {
  codigo_legado: 'Código Legado',
  regras_negocio: 'Regras de Negócio',
  arquitetura_software: 'Arquitetura de Software',
  seguranca_informacao: 'Segurança da Informação',
}

export function parseSynthesisByDomain(text: string): Array<{ domain: string; text: string }> {
  const matches = [...text.matchAll(/\[([a-z_]+)\]\s*/g)]
  if (matches.length === 0) return [{ domain: '', text }]

  return matches.map((match, index) => {
    const start = (match.index ?? 0) + match[0].length
    const end = index + 1 < matches.length ? matches[index + 1].index : text.length
    return { domain: match[1], text: text.slice(start, end).trim() }
  })
}

export function SynthesisByDomain({ text }: { text: string }) {
  const parts = parseSynthesisByDomain(text)
  return (
    <div className="workspace-synthesis-list">
      {parts.map((part, index) => (
        <div key={`${part.domain}-${index}`} className="workspace-synthesis-item">
          {part.domain && <span className="workspace-synthesis-domain">{domainLabels[part.domain] ?? part.domain}</span>}
          <p>{part.text}</p>
        </div>
      ))}
    </div>
  )
}

export function SkillResultCard({ result }: { result: SkillToolResult }) {
  return (
    <article className="workspace-execution-skill-card">
      <header>
        <div>
          <strong>{result.agente_emissor.nome}</strong>
          <span className="workspace-skill-card-domain">{domainLabels[result.agente_emissor.dominio] ?? result.agente_emissor.dominio}</span>
        </div>
        <span className={`workspace-confidence-pill workspace-confidence-${result.governanca.nivel_confianca.toLowerCase()}`}>
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
  )
}
