import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { FollowUpForm } from './FollowUpForm'

function renderForm(overrides: Partial<Parameters<typeof FollowUpForm>[0]> = {}) {
  const onAsk = vi.fn(async () => undefined)
  render(
    <FollowUpForm
      participatingDomains={['codigo_legado', 'Contabilidade']}
      onAsk={onAsk}
      submitting={false}
      pendingSince={null}
      error=""
      {...overrides}
    />,
  )
  return onAsk
}

describe('FollowUpForm', () => {
  it('pergunta a todos os agentes por padrão e limpa o campo depois', async () => {
    const user = userEvent.setup()
    const onAsk = renderForm()
    const question = screen.getByLabelText('Pergunta de acompanhamento')

    await user.type(question, 'Qual é o maior risco?')
    await user.click(screen.getByRole('button', { name: 'Perguntar' }))

    expect(onAsk).toHaveBeenCalledWith('Qual é o maior risco?', null)
    expect(question).toHaveValue('')
  })

  it('direciona a pergunta para a área escolhida, inclusive uma área livre', async () => {
    const user = userEvent.setup()
    const onAsk = renderForm()

    await user.type(screen.getByLabelText('Pergunta de acompanhamento'), 'E os impostos?')
    await user.selectOptions(screen.getByLabelText('Perguntar para'), 'Contabilidade')
    await user.click(screen.getByRole('button', { name: 'Perguntar' }))

    expect(onAsk).toHaveBeenCalledWith('E os impostos?', 'Contabilidade')
  })

  it('bloqueia nova pergunta enquanto os agentes respondem', () => {
    renderForm({ pendingSince: new Date().toISOString() })

    expect(screen.getByRole('button', { name: 'Perguntando…' })).toBeDisabled()
    expect(screen.getByText('Os agentes estão respondendo.')).toBeInTheDocument()
  })

  it('mostra o erro da pergunta anterior', () => {
    renderForm({ error: 'A pergunta falhou.' })

    expect(screen.getByText('A pergunta falhou.')).toBeInTheDocument()
  })
})
