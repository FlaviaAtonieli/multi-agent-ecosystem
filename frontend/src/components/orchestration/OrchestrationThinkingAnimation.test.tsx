import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { OrchestrationEvent } from '../../api/orchestrationApi'
import { OrchestrationThinkingAnimation } from './OrchestrationThinkingAnimation'

const START = new Date('2026-11-03T12:00:00Z').getTime()
let sequence = 0

function event(event_type: string, payload: Record<string, unknown> = {}, secondsAfterStart = 0): OrchestrationEvent {
  sequence += 1
  return {
    id: `evt-${sequence}`,
    sequence_number: sequence,
    event_type,
    actor: 'Orquestrador',
    title: event_type,
    message: '',
    payload,
    created_at: new Date(START + secondsAfterStart * 1000).toISOString(),
  }
}

const selected = (id: string, domain = id) => event('AGENT_SKILL_SELECTED', { agent_skill_id: id, domain })
const started = (id: string) => event('AGENT_SKILL_INVOCATION_STARTED', { agent_skill_id: id })
const completed = (id: string, latency_ms = 0) => event('AGENT_SKILL_INVOCATION_COMPLETED', { agent_skill_id: id, latency_ms })
const failed = (id: string) => event('AGENT_SKILL_INVOCATION_FAILED', { agent_skill_id: id })
const runStart = (max_parallel = 3) => event('ORCHESTRATION_EXECUTION_STARTED', { max_parallel })

function stepClass(label: string) {
  return screen.getByText(label).closest('li')?.className ?? ''
}

function renderPanel(events: OrchestrationEvent[]) {
  return render(<OrchestrationThinkingAnimation events={events} traceId="TRC-1" />)
}

describe('OrchestrationThinkingAnimation', () => {
  beforeEach(() => {
    sequence = 0
    vi.useFakeTimers({ toFake: ['Date', 'setInterval', 'clearInterval'], now: START })
  })

  it('mostra a seleção em andamento antes de escolher as skills', () => {
    renderPanel([runStart()])

    expect(stepClass('Selecionando Agent Skills')).toContain('is-active')
    expect(screen.queryByText(/Agent Skills concluídas/)).not.toBeInTheDocument()
  })

  it('mostra o estado real de cada skill', () => {
    renderPanel([
      runStart(),
      selected('codigo_legado'),
      selected('regras_negocio'),
      selected('Contabilidade'),
      started('codigo_legado'),
      started('regras_negocio'),
      completed('codigo_legado', 30000),
    ])

    expect(stepClass('Consultando Código Legado')).toContain('is-done')
    expect(stepClass('Consultando Regras de Negócio')).toContain('is-active')
    expect(stepClass('Consultando Contabilidade')).not.toMatch(/is-active|is-done/)
    expect(screen.getByText('1 de 3 Agent Skills concluídas.')).toBeInTheDocument()
  })

  it('calcula a estimativa com a latência real e o limite de paralelismo da execução', () => {
    const ids = ['a', 'b', 'c', 'd', 'e']
    renderPanel([runStart(2), ...ids.map((id) => selected(id)), started('a'), completed('a', 90000)])

    // 4 restantes em 2 rodadas de 90 s = 180 s; 5 no total em 3 rodadas = 270 s.
    expect(screen.getByText(/Tempo restante: cerca de 3 min \(cerca de 5 min no total\)/)).toBeInTheDocument()
  })

  it('conta uma skill que falhou como terminada, para o progresso não travar', () => {
    renderPanel([runStart(), selected('a'), selected('b'), started('a'), started('b'), completed('a'), failed('b')])

    expect(screen.getByText('2 de 2 Agent Skills concluídas.')).toBeInTheDocument()
    expect(screen.getByText(/Finalizando a resposta/)).toBeInTheDocument()
    expect(stepClass('Avaliando Quality Gate e consolidando')).toContain('is-active')
  })

  it('ao repetir uma execução, considera só os eventos da tentativa mais recente', () => {
    renderPanel([
      runStart(),
      selected('codigo_legado'),
      started('codigo_legado'),
      failed('codigo_legado'),
      runStart(),
      selected('regras_negocio'),
    ])

    expect(screen.getByText('0 de 1 Agent Skills concluídas.')).toBeInTheDocument()
    expect(screen.queryByText('Consultando Código Legado')).not.toBeInTheDocument()
  })

  it('conta o tempo a partir do início real, mesmo depois de recarregar a página', () => {
    vi.setSystemTime(START + 65_000)
    renderPanel([runStart()])
    const timer = screen.getByRole('timer')
    expect(timer).toHaveTextContent('01:05')

    act(() => {
      vi.advanceTimersByTime(2000)
    })

    expect(timer).toHaveTextContent('01:07')
  })

  it('ao recolher, mantém visível a etapa atual', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    renderPanel([runStart(), selected('a'), started('a')])
    const header = screen.getByRole('button', { expanded: true })

    await user.click(header)

    expect(header).toHaveAttribute('aria-expanded', 'false')
    expect(within(header).getByText('Consultando a')).toBeInTheDocument()
    expect(screen.queryByText(/Agent Skills concluídas/)).not.toBeInTheDocument()
  })
})
