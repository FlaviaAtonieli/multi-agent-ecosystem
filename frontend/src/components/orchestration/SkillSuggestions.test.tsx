import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { apiError, ApiResponse, mockApi } from '../../test/api'
import { SkillSuggestions } from './SkillSuggestions'

const URL = '/agent-skills/suggestions'

const suggestion = { id: 's1', name: 'Skill de Impostos', domain: 'Contabilidade', objective: 'Calcular impostos.', score: 0.62 }

function response(overrides: Record<string, unknown> = {}) {
  return {
    available: true,
    suggestions: [suggestion],
    best_clan_score: 0.2,
    covered_by_clan: false,
    catalog_gap: false,
    can_add_to_clan: true,
    ...overrides,
  }
}

function renderPanel(onAdded = vi.fn()) {
  render(
    <MemoryRouter>
      <SkillSuggestions clanId="clan-1" title="Título" problem="O problema." objective="O objetivo." context="O contexto." onAdded={onAdded} />
    </MemoryRouter>,
  )
  return onAdded
}

const check = (user: ReturnType<typeof userEvent.setup>) =>
  user.click(screen.getByRole('button', { name: 'Verificar skills que podem ajudar' }))

describe('SkillSuggestions', () => {
  it('só consulta quando a pessoa pede', () => {
    const api = mockApi({ [`POST ${URL}`]: response() })

    renderPanel()

    expect(api.callsTo('POST', URL)).toHaveLength(0)
  })

  it('envia a solicitação e mostra a skill sugerida com a similaridade', async () => {
    const user = userEvent.setup()
    const api = mockApi({ [`POST ${URL}`]: response() })
    renderPanel()

    await check(user)

    expect(await screen.findByText('Skill de Impostos')).toBeInTheDocument()
    expect(screen.getByText(/62%/)).toBeInTheDocument()
    expect(screen.getByText('Calcular impostos.')).toBeInTheDocument()
    expect(api.jsonBody('POST', URL)).toEqual({
      clan_id: 'clan-1',
      title: 'Título',
      problem: 'O problema.',
      objective: 'O objetivo.',
      context: 'O contexto.',
    })
  })

  it('adiciona a skill ao comitê e avisa o formulário', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      [`POST ${URL}`]: response(),
      'POST /clans/clan-1/skills': new ApiResponse(201, suggestion),
    })
    const onAdded = renderPanel()
    await check(user)

    await user.click(await screen.findByRole('button', { name: 'Adicionar Skill de Impostos ao comitê' }))

    expect(await screen.findByText(/Skill de Impostos entrou no comitê/)).toBeInTheDocument()
    expect(onAdded).toHaveBeenCalledWith('Contabilidade')
    expect(api.jsonBody('POST', '/clans/clan-1/skills')).toEqual({ agent_skill_id: 's1' })
    expect(screen.queryByRole('button', { name: 'Adicionar Skill de Impostos ao comitê' })).not.toBeInTheDocument()
  })

  it('sem permissão no comitê, mostra a sugestão sem o botão', async () => {
    const user = userEvent.setup()
    mockApi({ [`POST ${URL}`]: response({ can_add_to_clan: false }) })
    renderPanel()

    await check(user)

    await screen.findByText('Skill de Impostos')
    expect(screen.queryByRole('button', { name: /^Adicionar/ })).not.toBeInTheDocument()
    expect(screen.getByText(/Só o dono deste comitê pode adicionar/)).toBeInTheDocument()
  })

  it('avisa quando o comitê já cobre o assunto', async () => {
    const user = userEvent.setup()
    mockApi({ [`POST ${URL}`]: response({ suggestions: [], covered_by_clan: true }) })
    renderPanel()

    await check(user)

    expect(await screen.findByText(/As skills deste comitê já parecem cobrir/)).toBeInTheDocument()
  })

  it('avisa quando o catálogo não cobre o assunto e oferece criar uma skill', async () => {
    const user = userEvent.setup()
    mockApi({ [`POST ${URL}`]: response({ suggestions: [], catalog_gap: true }) })
    renderPanel()

    await check(user)

    expect(await screen.findByText(/Nenhuma skill do catálogo parece cobrir/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Criar uma skill' })).toHaveAttribute('href', '/agent-skills/new')
  })

  it('avisa quando o motor está indisponível, sem impedir o formulário', async () => {
    const user = userEvent.setup()
    mockApi({ [`POST ${URL}`]: response({ available: false, suggestions: [] }) })
    renderPanel()

    await check(user)

    expect(await screen.findByText(/sugestão de skills está indisponível/)).toBeInTheDocument()
  })

  it('mostra o erro quando a consulta é recusada', async () => {
    const user = userEvent.setup()
    mockApi({ [`POST ${URL}`]: apiError(429, 'Muitas tentativas.') })
    renderPanel()

    await check(user)

    expect(await screen.findByText('Muitas tentativas.')).toBeInTheDocument()
  })

  it('mostra o erro quando a skill não pode ser adicionada', async () => {
    const user = userEvent.setup()
    mockApi({
      [`POST ${URL}`]: response(),
      'POST /clans/clan-1/skills': apiError(403, 'Neste comitê, só o dono pode registrar Agent Skills.'),
    })
    const onAdded = renderPanel()
    await check(user)

    await user.click(await screen.findByRole('button', { name: 'Adicionar Skill de Impostos ao comitê' }))

    expect(await screen.findByText('Neste comitê, só o dono pode registrar Agent Skills.')).toBeInTheDocument()
    expect(onAdded).not.toHaveBeenCalled()
  })
})
