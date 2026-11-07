import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { OrchestrationExecutionResult, SkillToolResult } from '../../api/agentSkillsApi'
import { ExecutionResultPanel } from './ExecutionResultPanel'

function skill(nome: string, dominio: string, resumo: string): SkillToolResult {
  return {
    trace_id: 'TRC-1',
    agente_emissor: { nome, versao_prompt: null, dominio },
    analise_estruturada: { resumo_executivo: resumo, descobertas_tecnicas: [], impactos_mapeados: [] },
    governanca: { nivel_confianca: 'ALTO', justificativa_confianca: 'Base suficiente.', referencias_catalogo: [] },
  }
}

const execution: OrchestrationExecutionResult = {
  results: [
    skill('Programação de Jogos Web', 'programacao_jogos', 'Entregou o jogo em HTML, CSS e JavaScript.'),
    skill('Game Design', 'game_design', 'Definiu regras, turnos e condição de vitória.'),
  ],
  verdict: { approved: true, requires_human_review: false, reasons: [] },
  invocations_count: 2,
  consolidated_response: {
    id: 'c1',
    trace_id: 'TRC-1',
    technical_synthesis: '[programacao_jogos] Jogo entregue. [game_design] Regras definidas.',
    recommendations: ['Testar em celular.'],
    risks: ['Sem testes automatizados.'],
    limitations: [],
    overall_confidence_level: 'ALTO',
    quality_gate_approved: true,
    requires_human_review: false,
    participating_agents: ['Programação de Jogos Web', 'Game Design'],
    invocation_ids: ['i1', 'i2'],
    created_at: '2026-11-06T12:00:00Z',
  },
}

describe('ExecutionResultPanel', () => {
  it('organiza em resumo, material e resposta de cada agente, nessa ordem', () => {
    render(<ExecutionResultPanel execution={execution} material={<p>lista de arquivos</p>} />)

    const headings = screen.getAllByRole('heading', { level: 3 }).map((heading) => heading.textContent)
    expect(headings).toEqual(['Resumo', 'Resposta de cada agente (2)'])
    const material = screen.getByText('lista de arquivos')
    const agents = screen.getByRole('heading', { name: 'Resposta de cada agente (2)' })
    expect(screen.getByRole('heading', { name: 'Resumo' }).compareDocumentPosition(material)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING,
    )
    expect(material.compareDocumentPosition(agents)).toBe(Node.DOCUMENT_POSITION_FOLLOWING)
  })

  it('o resumo mostra quantos agentes responderam, riscos e recomendações', () => {
    render(<ExecutionResultPanel execution={execution} />)

    const summary = screen.getByRole('region', { name: 'Resumo' })
    expect(summary).toHaveTextContent('2 agentes responderam')
    expect(summary).toHaveTextContent('Testar em celular.')
    expect(summary).toHaveTextContent('Sem testes automatizados.')
  })

  it('os cards dos agentes começam fechados e abrem um a um', async () => {
    const user = userEvent.setup()
    render(<ExecutionResultPanel execution={execution} />)

    expect(screen.queryByText('Entregou o jogo em HTML, CSS e JavaScript.')).not.toBeInTheDocument()

    const card = screen.getByRole('button', { name: /Programação de Jogos Web/ })
    expect(card).toHaveAttribute('aria-expanded', 'false')
    await user.click(card)

    expect(card).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByText('Entregou o jogo em HTML, CSS e JavaScript.')).toBeInTheDocument()
    expect(screen.queryByText('Definiu regras, turnos e condição de vitória.')).not.toBeInTheDocument()
  })

  it('expande e recolhe todos de uma vez', async () => {
    const user = userEvent.setup()
    render(<ExecutionResultPanel execution={execution} />)

    await user.click(screen.getByRole('button', { name: 'Expandir todos' }))
    expect(screen.getByText('Entregou o jogo em HTML, CSS e JavaScript.')).toBeInTheDocument()
    expect(screen.getByText('Definiu regras, turnos e condição de vitória.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Recolher todos' }))
    expect(screen.queryByText('Definiu regras, turnos e condição de vitória.')).not.toBeInTheDocument()
  })

  it('cada card fechado já mostra área e confiança', () => {
    render(<ExecutionResultPanel execution={execution} />)

    const card = screen.getByRole('button', { name: /Game Design/ })
    expect(within(card).getByText('Game design')).toBeInTheDocument()
    expect(within(card).getByText('Alta')).toBeInTheDocument()
  })
})
