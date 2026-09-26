import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
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
// Rendered as a fixed corner widget (not inline in the page flow): the
// execute call can take a while, and pinning it to a corner keeps the rest of
// the request's details on screen and scrollable instead of being pushed down
// by a growing step list.
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

  return createPortal(
    <div className={`workspace-thinking-float${collapsed ? ' is-collapsed' : ''}`} role="status" aria-live="polite">
      <button
        type="button"
        className="workspace-thinking-float-header"
        onClick={() => setCollapsed((value) => !value)}
        aria-expanded={!collapsed}
      >
        <span className="workspace-thinking-orb" aria-hidden="true">
          <span className="workspace-thinking-orb-core" />
          <span className="workspace-thinking-orb-ring" />
          <span className="workspace-thinking-orb-ring workspace-thinking-orb-ring-delay" />
        </span>
        <span className="workspace-thinking-float-title">
          Processando orquestração
          {collapsed && <small>{currentStepLabel}</small>}
        </span>
        <span className="workspace-thinking-float-toggle" aria-hidden="true">
          {collapsed ? '▴' : '▾'}
        </span>
      </button>

      {!collapsed && (
        <div className="workspace-thinking-float-body">
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
            Rastreado via Trace ID <code>{traceId}</code> — cada etapa fica registrada na Auditoria assim que
            conclui, mesmo enquanto a orquestração ainda está em execução.
          </p>
        </div>
      )}
    </div>,
    document.body,
  )
}
