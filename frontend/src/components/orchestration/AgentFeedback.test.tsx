import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { AgentResponseFeedback } from '../../api/orchestrationApi'
import { apiError, ApiResponse, mockApi } from '../../test/api'
import { AgentFeedback } from './AgentFeedback'

const URL = '/orchestrations/TRC-1/skill-results/inv-1/feedback'

function saved(overrides: Partial<AgentResponseFeedback> = {}): AgentResponseFeedback {
  return { useful: true, reason: null, comment: null, updated_at: '2026-11-11T00:00:00Z', ...overrides }
}

function renderFeedback(initial: AgentResponseFeedback | null = null) {
  return render(<AgentFeedback traceId="TRC-1" invocationId="inv-1" agentName="Agente X" initial={initial} />)
}

describe('AgentFeedback', () => {
  it('marca como útil com um clique', async () => {
    const api = mockApi({ [`PUT ${URL}`]: saved() })
    renderFeedback()

    await userEvent.click(screen.getByRole('button', { name: 'Útil' }))

    expect(api.jsonBody('PUT', URL)).toEqual({ useful: true })
    expect(await screen.findByRole('button', { name: 'Útil' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('status')).toHaveTextContent('Avaliação salva')
  })

  it('clicar de novo em útil remove a avaliação', async () => {
    const api = mockApi({ [`DELETE ${URL}`]: new ApiResponse(204, null) })
    renderFeedback(saved())

    await userEvent.click(screen.getByRole('button', { name: 'Útil' }))

    expect(api.callsTo('DELETE', URL)).toHaveLength(1)
    expect(await screen.findByRole('button', { name: 'Útil' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('não útil pede o motivo antes de salvar', async () => {
    const api = mockApi({ [`PUT ${URL}`]: saved({ useful: false, reason: 'SEM_EVIDENCIA', comment: 'Faltou o módulo.' }) })
    renderFeedback()

    await userEvent.click(screen.getByRole('button', { name: 'Não útil' }))
    const save = screen.getByRole('button', { name: 'Salvar avaliação' })
    expect(save).toBeDisabled()
    expect(api.callsTo('PUT', URL)).toHaveLength(0)

    await userEvent.click(screen.getByRole('radio', { name: 'Sem evidência' }))
    await userEvent.type(screen.getByLabelText(/Comentário/), 'Faltou o módulo.')
    await userEvent.click(save)

    expect(api.jsonBody('PUT', URL)).toEqual({ useful: false, reason: 'SEM_EVIDENCIA', comment: 'Faltou o módulo.' })
    expect(await screen.findByText('Motivo: Sem evidência')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Não útil' })).toHaveAttribute('aria-pressed', 'true')
  })

  it('cancelar fecha o formulário sem salvar', async () => {
    const api = mockApi({})
    renderFeedback()

    await userEvent.click(screen.getByRole('button', { name: 'Não útil' }))
    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }))

    expect(screen.queryByRole('radio', { name: 'Incorreta' })).not.toBeInTheDocument()
    expect(api.callsTo('PUT', URL)).toHaveLength(0)
  })

  it('mostra a avaliação já salva', () => {
    mockApi({})
    renderFeedback(saved({ useful: false, reason: 'INCOMPLETA' }))

    expect(screen.getByRole('button', { name: 'Não útil' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByText('Motivo: Incompleta')).toBeInTheDocument()
  })

  it('mostra o erro da API', async () => {
    mockApi({ [`PUT ${URL}`]: apiError(404, 'Resposta do agente não encontrada.') })
    renderFeedback()

    await userEvent.click(screen.getByRole('button', { name: 'Útil' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Resposta do agente não encontrada.')
    expect(screen.getByRole('button', { name: 'Útil' })).toHaveAttribute('aria-pressed', 'false')
  })
})
