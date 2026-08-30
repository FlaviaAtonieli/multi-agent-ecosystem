import { FollowUpExchange } from '../../api/agentSkillsApi'
import { confidenceLabels, domainLabels, SkillResultCard, SynthesisByDomain } from './shared'

export function FollowUpExchangeCard({ exchange }: { exchange: FollowUpExchange }) {
  return (
    <article className="workspace-follow-up-exchange">
      <header className="workspace-follow-up-question">
        <span className="workspace-follow-up-badge">Pergunta {exchange.sequence_number}</span>
        {exchange.target_domain && (
          <span className="workspace-synthesis-domain">
            {domainLabels[exchange.target_domain] ?? exchange.target_domain}
          </span>
        )}
        <p>{exchange.question}</p>
        <small>{new Date(exchange.created_at).toLocaleString('pt-BR')}</small>
      </header>

      <div className="workspace-execution-summary">
        <span className={`workspace-status ${exchange.quality_gate_approved ? 'workspace-status-completed' : 'workspace-status-validating'}`}>
          {exchange.quality_gate_approved ? 'Aprovado pelo Quality Gate' : 'Requer revisão humana'}
        </span>
        <span className={`workspace-confidence-pill workspace-confidence-${exchange.overall_confidence_level.toLowerCase()}`}>
          Confiança geral: {confidenceLabels[exchange.overall_confidence_level]}
        </span>
      </div>

      <SynthesisByDomain text={exchange.synthesis} />

      {exchange.results.length > 0 && (
        <div className="workspace-execution-skills">
          {exchange.results.map((result, index) => (
            <SkillResultCard key={`${result.agente_emissor.nome}-${index}`} result={result} />
          ))}
        </div>
      )}
    </article>
  )
}
