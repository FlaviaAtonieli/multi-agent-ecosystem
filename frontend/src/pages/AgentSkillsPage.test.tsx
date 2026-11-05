import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { apiError, mockApi, testUser } from '../test/api'
import { AgentSkillsPage } from './AgentSkillsPage'

function skill(id: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    name: `Skill ${id}`,
    version: '1.0',
    domain: 'codigo_legado',
    status: 'approved',
    enabled: true,
    objective: 'Objetivo.',
    owner_id: null,
    visibility: 'OFFICIAL',
    clan_id: null,
    ...overrides,
  }
}

const catalog = [
  skill('sem-dono'),
  skill('oficial-minha', { owner_id: testUser.id }),
  skill('oficial-outra', { owner_id: 'outra-pessoa' }),
  skill('privada-minha', { owner_id: testUser.id, visibility: 'PRIVATE', domain: 'Contabilidade' }),
  skill('cla-meu', { owner_id: 'outra-pessoa', visibility: 'CLAN', clan_id: 'cla-1' }),
  skill('cla-alheio', { owner_id: 'outra-pessoa', visibility: 'CLAN', clan_id: 'cla-2' }),
  skill('desativada', { owner_id: testUser.id, enabled: false }),
]

const clans = [
  { id: 'cla-1', name: 'Meu clã', created_by_id: testUser.id },
  { id: 'cla-2', name: 'Clã alheio', created_by_id: 'outra-pessoa' },
]

function routes(overrides: Record<string, unknown> = {}) {
  return {
    'GET /auth/me': testUser,
    'GET /agent-skills?only_active=false': catalog,
    'GET /agent-skills/ranking?limit=5': [],
    'GET /clans?mine=true': clans,
    ...overrides,
  }
}

function renderPage() {
  return render(
    <AuthProvider>
      <MemoryRouter>
        <AgentSkillsPage />
      </MemoryRouter>
    </AuthProvider>,
  )
}

async function card(name: string) {
  const heading = await screen.findByRole('heading', { name })
  return heading.closest('article') as HTMLElement
}

describe('AgentSkillsPage', () => {
  it('avisa quando o catálogo não carrega', async () => {
    mockApi(routes({ 'GET /agent-skills?only_active=false': apiError(500, 'Erro ao buscar o catálogo.') }))

    renderPage()

    expect(await screen.findByText('Erro ao buscar o catálogo.')).toBeInTheDocument()
  })

  it('mostra o nome digitado de uma área livre', async () => {
    mockApi(routes())

    renderPage()

    expect(within(await card('Skill privada-minha')).getByText('Contabilidade')).toBeInTheDocument()
  })

  describe('quem pode gerenciar uma skill', () => {
    it.each([
      ['sem-dono', false],
      ['oficial-minha', true],
      ['oficial-outra', false],
      ['privada-minha', true],
      ['cla-alheio', false],
    ])('%s: botões visíveis = %s', async (id, visible) => {
      mockApi(routes())
      renderPage()
      const element = await card(`Skill ${id}`)
      // O dono do clã só é conhecido depois que a lista de clãs carrega.
      await screen.findByRole('option', { name: 'Clã · Meu clã' })

      expect(within(element).queryByRole('link', { name: 'Editar' }) !== null).toBe(visible)
      expect(within(element).queryByRole('button', { name: 'Desativar' }) !== null).toBe(visible)
    })

    it('o dono do clã gerencia uma skill do clã criada por outra pessoa', async () => {
      mockApi(routes())
      renderPage()
      const element = await card('Skill cla-meu')

      expect(await within(element).findByRole('button', { name: 'Desativar' })).toBeInTheDocument()
    })
  })

  describe('skill oficial sem dono', () => {
    const initialAccount = { 'GET /auth/me': { ...testUser, is_initial_account: true } }

    it('a conta inicial pode desativar, mas não editar', async () => {
      mockApi(routes(initialAccount))
      renderPage()
      const element = await card('Skill sem-dono')

      expect(await within(element).findByRole('button', { name: 'Desativar' })).toBeInTheDocument()
      expect(within(element).queryByRole('link', { name: 'Editar' })).not.toBeInTheDocument()
    })

    it('a conta inicial desativa e o card atualiza', async () => {
      const user = userEvent.setup()
      const api = mockApi(
        routes({ ...initialAccount, 'PATCH /agent-skills/sem-dono/disable': skill('sem-dono', { enabled: false }) }),
      )
      renderPage()
      const element = await card('Skill sem-dono')

      await user.click(await within(element).findByRole('button', { name: 'Desativar' }))

      expect(await within(element).findByRole('button', { name: 'Reativar' })).toBeInTheDocument()
      expect(api.callsTo('PATCH', '/agent-skills/sem-dono/disable')).toHaveLength(1)
    })

    it('a conta inicial não ganha botões nas skills de outras pessoas', async () => {
      mockApi(routes(initialAccount))
      renderPage()
      const element = await card('Skill oficial-outra')
      await within(await card('Skill sem-dono')).findByRole('button', { name: 'Desativar' })

      expect(within(element).queryByRole('button', { name: 'Desativar' })).not.toBeInTheDocument()
    })
  })

  describe('ativar e desativar', () => {
    it('desativa a skill e atualiza o card', async () => {
      const user = userEvent.setup()
      const api = mockApi(
        routes({ 'PATCH /agent-skills/oficial-minha/disable': skill('oficial-minha', { owner_id: testUser.id, enabled: false }) }),
      )
      renderPage()
      const element = await card('Skill oficial-minha')

      await user.click(within(element).getByRole('button', { name: 'Desativar' }))

      expect(await within(element).findByRole('button', { name: 'Reativar' })).toBeInTheDocument()
      expect(within(element).getByText('Indisponível')).toBeInTheDocument()
      expect(api.callsTo('PATCH', '/agent-skills/oficial-minha/disable')).toHaveLength(1)
    })

    it('reativa uma skill desativada', async () => {
      const user = userEvent.setup()
      mockApi(routes({ 'PATCH /agent-skills/desativada/enable': skill('desativada', { owner_id: testUser.id }) }))
      renderPage()
      const element = await card('Skill desativada')

      await user.click(within(element).getByRole('button', { name: 'Reativar' }))

      expect(await within(element).findByText('Disponível')).toBeInTheDocument()
    })

    it('mantém o estado e mostra o erro quando o backend recusa', async () => {
      const user = userEvent.setup()
      mockApi(routes({ 'PATCH /agent-skills/oficial-minha/disable': apiError(403, 'Só quem criou a skill pode alterá-la.') }))
      renderPage()
      const element = await card('Skill oficial-minha')

      await user.click(within(element).getByRole('button', { name: 'Desativar' }))

      expect(await screen.findByText('Só quem criou a skill pode alterá-la.')).toBeInTheDocument()
      expect(within(element).getByText('Disponível')).toBeInTheDocument()
    })
  })

  describe('filtros', () => {
    const names = () => screen.getAllByRole('heading', { level: 3 }).map((item) => item.textContent)

    it('busca pelo nome, sem diferenciar maiúsculas', async () => {
      const user = userEvent.setup()
      mockApi(routes())
      renderPage()
      await card('Skill sem-dono')

      await user.type(screen.getByRole('searchbox'), 'PRIVADA')

      expect(names()).toEqual(['Skill privada-minha'])
    })

    it('filtra por estado e mostra a contagem de cada um', async () => {
      const user = userEvent.setup()
      mockApi(routes())
      renderPage()
      await card('Skill sem-dono')

      await user.click(screen.getByRole('button', { name: 'Indisponíveis · 1' }))

      expect(names()).toEqual(['Skill desativada'])
    })

    it.each([
      ['Oficiais do ecossistema', ['Skill sem-dono', 'Skill oficial-minha', 'Skill oficial-outra', 'Skill desativada']],
      ['Minhas privadas', ['Skill privada-minha']],
      ['Clã · Meu clã', ['Skill cla-meu']],
    ])('filtra pela origem: %s', async (option, expected) => {
      const user = userEvent.setup()
      mockApi(routes())
      renderPage()
      await screen.findByRole('option', { name: 'Clã · Meu clã' })

      await user.selectOptions(screen.getByLabelText('Filtrar por origem'), option)

      expect(names()).toEqual(expected)
    })

    it('explica quando o filtro não encontra nada', async () => {
      const user = userEvent.setup()
      mockApi(routes())
      renderPage()
      await card('Skill sem-dono')

      await user.type(screen.getByRole('searchbox'), 'não existe')

      expect(screen.getByText('Nenhuma skill corresponde ao filtro atual.')).toBeInTheDocument()
    })
  })
})
