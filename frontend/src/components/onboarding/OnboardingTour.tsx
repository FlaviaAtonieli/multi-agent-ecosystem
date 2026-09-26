import { CSSProperties, useEffect, useState } from 'react'

type TourStep = {
  selector: string
  title: string
  description: string
}

const steps: TourStep[] = [
  {
    selector: '[data-tour="nav"]',
    title: 'Bem-vindo ao AgentHub',
    description: 'Aqui você acompanha todas as solicitações e o estado do ecossistema de agentes em tempo real.',
  },
  {
    selector: '[data-tour="new-request-button"]',
    title: 'Toda demanda começa aqui',
    description:
      'Um assistente guiado em 3 passos garante que o Orientador de Interação receba contexto suficiente logo na primeira tentativa.',
  },
  {
    selector: '[data-tour="pending-highlight"]',
    title: 'Fique de olho nas pendências',
    description:
      'Quando uma solicitação precisa de mais informações, ela aparece aqui com um atalho para completar rapidamente.',
  },
  {
    selector: '[data-tour="activity-feed"]',
    title: 'Acompanhe cada passo',
    description:
      'Todo evento do fluxo — decisões automáticas e ações manuais — fica registrado aqui, com origem e horário.',
  },
]

const SPOTLIGHT_PADDING = 8
const TOOLTIP_WIDTH = 320
const TOOLTIP_ESTIMATED_HEIGHT = 190

// Tries right, then below, then above, then left of the target -- a plain
// below/above heuristic breaks for a tall, narrow target like the full-height
// sidebar (no room above or below within the viewport at all).
function placeTooltip(rect: DOMRect): { top: number; left: number } {
  const viewportWidth = window.innerWidth
  const viewportHeight = window.innerHeight
  const gap = SPOTLIGHT_PADDING + 14

  const spaceRight = viewportWidth - rect.right
  if (spaceRight > TOOLTIP_WIDTH + gap + 16) {
    return {
      left: rect.right + gap,
      top: Math.min(Math.max(16, rect.top), viewportHeight - TOOLTIP_ESTIMATED_HEIGHT - 16),
    }
  }

  const clampedLeft = Math.min(Math.max(16, rect.left), viewportWidth - TOOLTIP_WIDTH - 16)
  const spaceBelow = viewportHeight - rect.bottom
  if (spaceBelow > TOOLTIP_ESTIMATED_HEIGHT + gap) {
    return { left: clampedLeft, top: rect.bottom + gap }
  }

  const spaceAbove = rect.top
  if (spaceAbove > TOOLTIP_ESTIMATED_HEIGHT + gap) {
    return { left: clampedLeft, top: Math.max(16, rect.top - TOOLTIP_ESTIMATED_HEIGHT - gap) }
  }

  return {
    left: Math.max(16, rect.left - TOOLTIP_WIDTH - gap),
    top: Math.min(Math.max(16, rect.top), viewportHeight - TOOLTIP_ESTIMATED_HEIGHT - 16),
  }
}

export function OnboardingTour({ onFinish }: { onFinish: () => void }) {
  const [stepIndex, setStepIndex] = useState(0)
  const [rect, setRect] = useState<DOMRect | null>(null)

  useEffect(() => {
    const step = steps[stepIndex]
    const target = document.querySelector(step.selector)
    if (!target) {
      setRect(null)
      return
    }

    target.scrollIntoView({ block: 'center', behavior: 'smooth' })
    const measure = () => setRect(target.getBoundingClientRect())
    measure()
    const timeout = window.setTimeout(measure, 320)
    window.addEventListener('resize', measure)
    return () => {
      window.clearTimeout(timeout)
      window.removeEventListener('resize', measure)
    }
  }, [stepIndex])

  const step = steps[stepIndex]
  const isLast = stepIndex === steps.length - 1

  function next() {
    if (isLast) {
      onFinish()
      return
    }
    setStepIndex((current) => current + 1)
  }

  if (!rect) return null

  const spotlightStyle: CSSProperties = {
    top: rect.top - SPOTLIGHT_PADDING,
    left: rect.left - SPOTLIGHT_PADDING,
    width: rect.width + SPOTLIGHT_PADDING * 2,
    height: rect.height + SPOTLIGHT_PADDING * 2,
  }

  const tooltipStyle: CSSProperties = { ...placeTooltip(rect), width: TOOLTIP_WIDTH }

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-spotlight" style={spotlightStyle} />
      <div key={stepIndex} className="onboarding-tooltip fade-up" style={tooltipStyle}>
        <span className="onboarding-step-count">Passo {stepIndex + 1} de {steps.length}</span>
        <h3>{step.title}</h3>
        <p>{step.description}</p>
        <div className="onboarding-actions">
          <button type="button" className="onboarding-skip" onClick={onFinish}>Pular tour</button>
          <button type="button" className="workspace-primary-action" onClick={next}>
            {isLast ? 'Concluir' : 'Próximo →'}
          </button>
        </div>
      </div>
    </div>
  )
}
