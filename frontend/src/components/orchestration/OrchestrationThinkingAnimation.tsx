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
//
// Rendered inline at the top of the page flow (not a floating widget): it
// takes over the spot the result card occupies once the response is ready,
// so the transition from "processando" to "resposta" reads as the same card
// updating in place.
export function OrchestrationThinkingAnimation({ domains, traceId }: Props) {
  const steps = [
    'Selecionando Agent Skills para o(s) domínio(s) solicitado(s)',
    'Recuperando contexto relevante (RAG)',
    ...domains.map((domain) => `Consultando ${domainLabels[domain] ?? domain}`),
    'Avaliando Quality Gate',
    'Consolidando resposta final',
  ]

  const [stepIndex, setStepIndex] = useState(0)
  const [collapsed, setCollapsed] = useState(false)

  useEffect(() => {
    if (stepIndex >= steps.length - 1) return
    const timer = window.setTimeout(() => setStepIndex((current) => current + 1), STEP_INTERVAL_MS)
    return () => window.clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepIndex])

  const currentStepLabel = steps[stepIndex]

  return (
    <article className="workspace-panel workspace-thinking-panel" role="status" aria-live="polite">
      <button
        type="button"
        className="workspace-thinking-panel-header"
        onClick={() => setCollapsed((value) => !value)}
        aria-expanded={!collapsed}
      >
        <span className="workspace-thinking-orb" aria-hidden="true">
          <span className="workspace-thinking-orb-halo" />
          <span className="workspace-thinking-orb-ring" />
          <span className="workspace-thinking-orb-ring workspace-thinking-orb-ring-delay" />
          <span className="workspace-thinking-orb-orbit workspace-thinking-orb-orbit-1">
            <span className="workspace-thinking-orb-satellite" />
          </span>
          <span className="workspace-thinking-orb-orbit workspace-thinking-orb-orbit-2">
            <span className="workspace-thinking-orb-satellite" />
          </span>
          <span className="workspace-thinking-orb-core" />
        </span>
        <span className="workspace-thinking-panel-title">
          Processando orquestração
          {collapsed && <small>{currentStepLabel}</small>}
        </span>
        <code className="workspace-thinking-panel-trace">{traceId}</code>
        <span className="workspace-thinking-panel-toggle" aria-hidden="true">
          {collapsed ? '▸' : '▾'}
        </span>
      </button>

      {!collapsed && (
        <div className="workspace-thinking-panel-body">
          <ul className="workspace-thinking-steps-grid">
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
        </div>
      )}
    </article>
  )
}
