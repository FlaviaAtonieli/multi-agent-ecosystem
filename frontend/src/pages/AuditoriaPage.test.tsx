import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { mockApi } from '../test/api'
import { AuditoriaPage } from './AuditoriaPage'

const page = {
  items: [
    {
      id: 'e1',
      title: 'Contexto qualificado',
      actor: 'INTERACTION_GUIDE',
      event_type: 'CONTEXT_QUALIFIED',
      request_title: 'Limite de crédito',
      request_trace_id: 'TRC-1',
      created_at: '2026-11-05T12:00:00Z',
    },
  ],
  total: 1,
  stats: { events_today: 1, automated_decisions_today: 1, manual_interventions_today: 0, compliance_alerts_today: 0 },
}

function renderPage() {
  mockApi({ 'GET /audit/events?days=7&limit=100': page })
  render(
    <MemoryRouter>
      <AuditoriaPage />
    </MemoryRouter>,
  )
}

describe('ajuda da auditoria', () => {
  it('explica para que serve e como usar, passo a passo', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Contexto qualificado')

    await user.click(screen.getByRole('button', { name: 'Como usar a auditoria' }))

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('Passo 1 de 5')
    expect(dialog).toHaveTextContent('Para que serve')

    for (const title of ['O que os números contam', 'Encontre um evento', 'Do evento à análise', 'Leve para fora']) {
      await user.click(screen.getByRole('button', { name: 'Próximo →' }))
      expect(await screen.findByRole('dialog')).toHaveTextContent(title)
    }
    await user.click(screen.getByRole('button', { name: 'Concluir' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('pode ser fechada a qualquer momento', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Contexto qualificado')

    await user.click(screen.getByRole('button', { name: 'Como usar a auditoria' }))
    await user.click(await screen.findByRole('button', { name: 'Fechar ajuda' }))

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('explica cada indicador com as regras do sistema', async () => {
    const user = userEvent.setup()
    renderPage()
    await screen.findByText('Contexto qualificado')

    await user.click(screen.getByRole('button', { name: 'Como usar a auditoria' }))
    await user.click(screen.getByRole('button', { name: 'Próximo →' }))

    const dialog = await screen.findByRole('dialog')
    expect(dialog).toHaveTextContent('falha de IA')
    expect(dialog).toHaveTextContent('rejeitada na revisão humana')
  })
})
