import { useEffect, useState } from 'react'
import { OrchestrationEvent } from '../../api/orchestrationApi'
import { domainLabels } from './shared'

// Média medida em produção (11/2026) com openai/gpt-5-mini. Só vale até a
// primeira skill terminar; depois a estimativa usa o tempo real desta execução.
const DEFAULT_SECONDS_PER_SKILL = 45

interface Props {
  events: OrchestrationEvent[]
  traceId: string
}

function formatElapsed(totalSeconds: number) {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

function formatEstimate(totalSeconds: number) {
  if (totalSeconds < 60) return 'menos de 1 min'
  return `cerca de ${Math.ceil(totalSeconds / 60)} min`
}

function latestRunEvents(events: OrchestrationEvent[]) {
  // Uma nova tentativa depois de uma falha mantém os eventos antigos na linha
  // do tempo: o progresso considera só os da execução mais recente.
  const startIndex = events.map((event) => event.event_type).lastIndexOf('ORCHESTRATION_EXECUTION_STARTED')
  return startIndex === -1 ? [] : events.slice(startIndex)
}

// Reflete o andamento real: os eventos vêm da linha do tempo que o backend grava
// a cada etapa. Fica no lugar do card de resultado, então a passagem de
// "processando" para "resposta" parece o mesmo card sendo atualizado.
export function OrchestrationThinkingAnimation({ events, traceId }: Props) {
  const [collapsed, setCollapsed] = useState(false)
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const runEvents = latestRunEvents(events)
  const eventsOfType = (type: string) => runEvents.filter((event) => event.event_type === type)
  const selected = eventsOfType('AGENT_SKILL_SELECTED')
  const started = eventsOfType('AGENT_SKILL_INVOCATION_STARTED')
  const completed = eventsOfType('AGENT_SKILL_INVOCATION_COMPLETED')
  const finished = [...completed, ...eventsOfType('AGENT_SKILL_INVOCATION_FAILED')]

  const finishedIds = new Set(finished.map((event) => event.payload.agent_skill_id))
  const activeId = started.map((event) => event.payload.agent_skill_id).find((id) => !finishedIds.has(id))

  const skillSteps = selected.map((event) => {
    const domain = String(event.payload.domain)
    const skillId = event.payload.agent_skill_id
    return {
      key: String(skillId),
      label: `Consultando ${domainLabels[domain] ?? domain}`,
      state: finishedIds.has(skillId) ? 'is-done' : skillId === activeId ? 'is-active' : '',
    }
  })
  const allFinished = selected.length > 0 && finished.length >= selected.length
  const steps = [
    { key: 'selection', label: 'Selecionando Agent Skills', state: selected.length > 0 ? 'is-done' : 'is-active' },
    ...skillSteps,
    { key: 'consolidation', label: 'Avaliando Quality Gate e consolidando', state: allFinished ? 'is-active' : '' },
  ]
  const currentStepLabel = steps.find((step) => step.state === 'is-active')?.label ?? 'Processando'

  const startedAt = runEvents[0] ? new Date(runEvents[0].created_at).getTime() : now
  const elapsedSeconds = Math.max(0, Math.floor((now - startedAt) / 1000))

  const latencies = completed.map((event) => Number(event.payload.latency_ms)).filter((value) => value > 0)
  const secondsPerSkill =
    latencies.length > 0
      ? latencies.reduce((sum, value) => sum + value, 0) / latencies.length / 1000
      : DEFAULT_SECONDS_PER_SKILL
  const remainingSeconds = Math.round((selected.length - finished.length) * secondsPerSkill)
  const totalSeconds = Math.round(selected.length * secondsPerSkill)

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
        {/* aria-live="off": sem isso, o leitor de tela anunciaria cada segundo. */}
        <span className="workspace-thinking-panel-timer" role="timer" aria-live="off">
          {formatElapsed(elapsedSeconds)}
        </span>
        <code className="workspace-thinking-panel-trace">{traceId}</code>
        <span className="workspace-thinking-panel-toggle" aria-hidden="true">
          {collapsed ? '▸' : '▾'}
        </span>
      </button>

      {!collapsed && (
        <div className="workspace-thinking-panel-body">
          {selected.length > 0 && (
            <p className="workspace-thinking-estimate">
              <strong>{finished.length} de {selected.length} Agent Skills concluídas.</strong>{' '}
              {allFinished
                ? 'Finalizando a resposta.'
                : `Tempo restante: ${formatEstimate(remainingSeconds)} (${formatEstimate(totalSeconds)} no total).`}{' '}
              Pode sair desta página: a análise continua e o resultado fica salvo.
            </p>
          )}
          <ul className="workspace-thinking-steps-grid">
            {steps.map((step) => (
              <li key={step.key} className={`workspace-thinking-step ${step.state}`.trim()}>
                <span className="workspace-thinking-marker" />
                {step.label}
              </li>
            ))}
          </ul>
        </div>
      )}
    </article>
  )
}
