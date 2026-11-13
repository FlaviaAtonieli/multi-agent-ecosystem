import { act, render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ClanRepository } from '../../api/clansApi'
import { apiError, ApiResponse, mockApi } from '../../test/api'
import { ClanRepositories } from './ClanRepositories'

const LIST = '/clans/clan-1/repositories'

function repository(overrides: Partial<ClanRepository> = {}): ClanRepository {
  return {
    id: 'repo-1',
    url: 'https://github.com/acme/faturamento',
    owner: 'acme',
    name: 'faturamento',
    status: 'READY',
    error_message: null,
    file_count: 3,
    chunk_count: 5,
    created_at: '2026-11-13T00:00:00Z',
    indexed_at: '2026-11-13T00:01:00Z',
    ...overrides,
  }
}

function renderSection(props: Partial<{ canSee: boolean; canChange: boolean }> = {}) {
  return render(<ClanRepositories clanId="clan-1" canSee canChange {...props} />)
}

describe('ClanRepositories', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })
  afterEach(() => {
    vi.useRealTimers()
  })
  const setupUser = () => userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

  it('lista os repositórios com o status e o motivo da falha', async () => {
    mockApi({
      [`GET ${LIST}`]: [
        repository(),
        repository({ id: 'repo-2', name: 'segredo', status: 'FAILED', error_message: 'O repositório é privado.' }),
      ],
    })
    renderSection()

    const ready = await screen.findByRole('listitem', { name: 'acme/faturamento' })
    expect(within(ready).getByText('Pronto · 3 arquivos · 5 trechos')).toBeInTheDocument()
    const failed = screen.getByRole('listitem', { name: 'acme/segredo' })
    expect(within(failed).getByText('Falhou')).toBeInTheDocument()
    expect(within(failed).getByText('O repositório é privado.')).toBeInTheDocument()
  })

  it('adiciona e acompanha a indexação até ficar pronto', async () => {
    let current: ClanRepository[] = []
    const api = mockApi({
      [`GET ${LIST}`]: () => current,
      [`POST ${LIST}`]: () => {
        current = [repository({ status: 'INDEXING', file_count: 0, chunk_count: 0, indexed_at: null })]
        return new ApiResponse(201, current[0])
      },
    })
    const user = setupUser()
    renderSection()
    await screen.findByText('Nenhum repositório neste comitê ainda.')

    await user.type(screen.getByLabelText('Endereço do repositório no GitHub'), 'https://github.com/acme/faturamento')
    await user.click(screen.getByRole('button', { name: 'Adicionar repositório' }))

    expect(api.jsonBody('POST', LIST)).toEqual({ url: 'https://github.com/acme/faturamento' })
    expect(await screen.findByText('Indexando…')).toBeInTheDocument()

    current = [repository()]
    await act(async () => {
      await vi.advanceTimersByTimeAsync(3000)
    })

    expect(await screen.findByText('Pronto · 3 arquivos · 5 trechos')).toBeInTheDocument()
  })

  it('mostra o motivo quando a API recusa o endereço', async () => {
    mockApi({
      [`GET ${LIST}`]: [],
      [`POST ${LIST}`]: apiError(422, 'Informe o endereço de um repositório público do GitHub.'),
    })
    const user = setupUser()
    renderSection()
    await screen.findByText('Nenhum repositório neste comitê ainda.')

    await user.type(screen.getByLabelText('Endereço do repositório no GitHub'), 'https://gitlab.com/a/b')
    await user.click(screen.getByRole('button', { name: 'Adicionar repositório' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Informe o endereço de um repositório público do GitHub.')
  })

  it('remove o repositório', async () => {
    let current = [repository()]
    const api = mockApi({
      [`GET ${LIST}`]: () => current,
      [`DELETE ${LIST}/repo-1`]: () => {
        current = []
        return new ApiResponse(204, null)
      },
    })
    const user = setupUser()
    renderSection()

    await user.click(await screen.findByRole('button', { name: 'Remover acme/faturamento' }))

    expect(api.callsTo('DELETE', `${LIST}/repo-1`)).toHaveLength(1)
    expect(await screen.findByText('Nenhum repositório neste comitê ainda.')).toBeInTheDocument()
  })

  it('indexa de novo', async () => {
    let current = [repository()]
    const api = mockApi({
      [`GET ${LIST}`]: () => current,
      [`POST ${LIST}/repo-1/reindex`]: () => {
        current = [repository({ status: 'PENDING' })]
        return new ApiResponse(202, current[0])
      },
    })
    const user = setupUser()
    renderSection()

    await user.click(await screen.findByRole('button', { name: 'Indexar acme/faturamento de novo' }))

    expect(api.callsTo('POST', `${LIST}/repo-1/reindex`)).toHaveLength(1)
    expect(await screen.findByText('Na fila')).toBeInTheDocument()
  })

  it('sem permissão, só mostra a lista', async () => {
    mockApi({ [`GET ${LIST}`]: [repository()] })
    renderSection({ canChange: false })

    await screen.findByRole('listitem', { name: 'acme/faturamento' })
    expect(screen.queryByLabelText('Endereço do repositório no GitHub')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Remover/ })).not.toBeInTheDocument()
  })

  it('quem não é membro de um comitê fechado não vê os repositórios', () => {
    const api = mockApi({})
    renderSection({ canSee: false, canChange: false })

    expect(screen.getByText('Só membros do comitê enxergam os repositórios dele.')).toBeInTheDocument()
    expect(api.calls).toHaveLength(0)
  })
})
