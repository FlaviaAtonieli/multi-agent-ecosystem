import { useEffect, useState } from 'react'
import { AgentSkillDomain } from '../../api/agentSkillsApi'
import { domainLabels } from './shared'

const STEP_INTERVAL_MS = 2600

interface Props {
  domains: AgentSkillDomain[]
  traceId: string
}

// Purely a perceived-progress animation on the frontend -- the real execute
// call is a single synchronous request with no server-sent progress today, so
// this never claims to reflect the exact backend step in real time. It stays
// honest by only naming stages/domains that are actually part of this
// request's real pipeline (RFC): skill selection, RAG retrieval, one step per
// requested domain, Quality Gate, consolidation -- not decorative filler.
export function OrchestrationThinkingAnimation({ domains, traceId }: Props) {
  const steps = [
    'Selecionando Agent Skills para o(s) domínio(s) solicitado(s)',
    'Recuperando contexto relevante (RAG)',
    ...domains.map((domain) => `Consultando ${domainLabels[domain] ?? domain}`),
    'Avaliando Quality Gate',
    'Consolidando resposta final',
  ]

  const [stepIndex, setStepIndex] = useState(0)

  useEffect(() => {
    if (stepIndex >= steps.length - 1) return
    const timer = window.setTimeout(() => setStepIndex((current) => current + 1), STEP_INTERVAL_MS)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepIndex])

  return (
    <div className="workspace-thinking" role="status" aria-live="polite">
      <ul className="workspace-thinking-steps">
        {steps.map((label, index) => (
          <li
            key={label}
            className={
              index < stepIndex
                ? 'workspace-thinking-step is-done'
                : index === stepIndex
                  ? 'workspace-thinking-step is-active'
                  : 'workspace-thinking-step'
            }
          >
            <span className="workspace-thinking-marker" />
            {label}
          </li>
        ))}
      </ul>
      <p className="workspace-thinking-trace">
        <span className="workspace-thinking-dot" />
        Rastreado via Trace ID <code>{traceId}</code> — cada etapa fica registrada na Auditoria assim que
        conclui, mesmo enquanto a orquestração ainda está em execução.
      </p>
    </div>
  )
}
