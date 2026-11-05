import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { apiError, ApiResponse, mockApi, testUser } from '../test/api'
import { ClansPage } from './ClansPage'

function skill(id: string, overrides: Record<string, unknown> = {}) {
  return { id, name: `Skill ${id}`, version: '1.0', objective: 'Objetivo.', enabled: true, ...overrides }
}

function clan(overrides: Record<string, unknown> = {}) {
  return {
    id: 'clan-1',
    name: 'Clã de Teste',
    created_by_id: testUser.id,
    created_at: '2026-11-01T00:00:00Z',
    member_count: 1,
    is_open: false,
    skills_policy: 'ALL_MEMBERS',
    members_policy: 'ALL_MEMBERS',
    members: [{ user_id: testUser.id, name: testUser.name, email: testUser.email, joined_at: '2026-11-01T00:00:00Z' }],
    ...overrides,
  }
}

const member = { user_id: testUser.id, name: testUser.name, email: testUser.email, joined_at: '2026-11-01T00:00:00Z' }
const someoneElse = { user_id: 'outra', name: 'Outra', email: 'outra@example.com', joined_at: '2026-11-01T00:00:00Z' }

function routes(detail = clan(), overrides: Record<string, unknown> = {}) {
  return {
    'GET /auth/me': testUser,
    'GET /clans': [detail],
    'GET /clans/clan-1': detail,
    'GET /clans/clan-1/skills': [skill('dentro')],
    'GET /agent-skills?only_active=false': [skill('dentro'), skill('fora'), skill('desligada', { enabled: false })],
    ...overrides,
  }
}

async function openClan(user: ReturnType<typeof userEvent.setup>) {
  render(
    <AuthProvider>
      <MemoryRouter>
        <ClansPage />
      </MemoryRouter>
    </AuthProvider>,
  )
  await user.click(await screen.findByRole('button', { name: /Clã de Teste/ }))
}

describe('Agent Skills do clã', () => {
  it('mostra as skills que vieram do clã, mesmo sem serem exclusivas dele', async () => {
    const user = userEvent.setup()
    mockApi(routes())

    await openClan(user)

    expect(await screen.findByText('Skill dentro')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remover Skill fora do clã' })).not.toBeInTheDocument()
  })

  it('oferece só as skills ativas que ainda não estão no clã', async () => {
    const user = userEvent.setup()
    mockApi(routes())

    await openClan(user)
    const select = await screen.findByRole('combobox', { name: 'Skill para adicionar' })

    expect(screen.getByRole('option', { name: 'Skill fora' })).toBeInTheDocument()
    expect(select).not.toHaveTextContent('Skill dentro')
    expect(select).not.toHaveTextContent('Skill desligada')
  })

  it('adiciona uma skill e atualiza a lista', async () => {
    const user = userEvent.setup()
    let inClan = [skill('dentro')]
    const api = mockApi(
      routes(clan(), {
        'GET /clans/clan-1/skills': () => inClan,
        'POST /clans/clan-1/skills': () => {
          inClan = [skill('dentro'), skill('fora')]
          return new ApiResponse(201, skill('fora'))
        },
      }),
    )
    await openClan(user)

    await user.selectOptions(await screen.findByRole('combobox', { name: 'Skill para adicionar' }), 'fora')
    await user.click(screen.getByRole('button', { name: 'Adicionar skill' }))

    expect(await screen.findByRole('button', { name: 'Remover Skill fora do clã' })).toBeInTheDocument()
    expect(api.jsonBody('POST', '/clans/clan-1/skills')).toEqual({ agent_skill_id: 'fora' })
  })

  it('remove uma skill do clã', async () => {
    const user = userEvent.setup()
    let inClan = [skill('dentro')]
    const api = mockApi(
      routes(clan(), {
        'GET /clans/clan-1/skills': () => inClan,
        'DELETE /clans/clan-1/skills/dentro': () => {
          inClan = []
          return new ApiResponse(204)
        },
      }),
    )
    await openClan(user)

    await user.click(await screen.findByRole('button', { name: 'Remover Skill dentro do clã' }))

    expect(await screen.findByText(/Nenhuma skill neste clã ainda/)).toBeInTheDocument()
    expect(api.callsTo('DELETE', '/clans/clan-1/skills/dentro')).toHaveLength(1)
  })

  it('mostra o motivo quando o backend recusa', async () => {
    const user = userEvent.setup()
    mockApi(routes(clan(), { 'POST /clans/clan-1/skills': apiError(409, 'Esta Agent Skill já está no clã.') }))
    await openClan(user)

    await user.selectOptions(await screen.findByRole('combobox', { name: 'Skill para adicionar' }), 'fora')
    await user.click(screen.getByRole('button', { name: 'Adicionar skill' }))

    expect(await screen.findByText('Esta Agent Skill já está no clã.')).toBeInTheDocument()
  })

  it('não deixa alterar quando só o dono pode', async () => {
    const user = userEvent.setup()
    mockApi(routes(clan({ created_by_id: 'outra', skills_policy: 'OWNER_ONLY', members: [member, someoneElse] })))

    await openClan(user)
    await screen.findByText('Skill dentro')

    expect(screen.queryByRole('combobox', { name: 'Skill para adicionar' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Remover Skill/ })).not.toBeInTheDocument()
  })

  it('mostra as skills de um clã aberto antes de entrar, sem deixar alterar', async () => {
    const user = userEvent.setup()
    mockApi(routes(clan({ created_by_id: 'outra', is_open: true, members: [someoneElse] })))

    await openClan(user)

    expect(await screen.findByText('Skill dentro')).toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Skill para adicionar' })).not.toBeInTheDocument()
  })

  it('em clã fechado de outra pessoa, explica que só membros veem', async () => {
    const user = userEvent.setup()
    mockApi(
      routes(clan({ created_by_id: 'outra', members: [someoneElse] }), {
        'GET /clans/clan-1/skills': apiError(403, 'Só um membro pode ver.'),
      }),
    )

    await openClan(user)

    expect(await screen.findByText('Só membros do clã enxergam as Agent Skills dele.')).toBeInTheDocument()
  })
})
