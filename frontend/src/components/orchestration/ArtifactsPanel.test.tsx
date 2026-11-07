import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { apiError, mockApi } from '../../test/api'
import { ArtifactsPanel } from './ArtifactsPanel'

const LIST = '/orchestrations/TRC-1/artifacts'

function artifact(id: string, filename: string, overrides: Record<string, unknown> = {}) {
  return {
    id,
    filename,
    size_bytes: 2048,
    agent_skill_name: 'Skill de Impostos',
    domain: 'Contabilidade',
    created_at: '2026-11-04T12:00:00Z',
    ...overrides,
  }
}

function renderPanel(refreshKey = 0) {
  return render(<ArtifactsPanel traceId="TRC-1" refreshKey={refreshKey} />)
}

describe('ArtifactsPanel', () => {
  it('não aparece quando a resposta não tem arquivos', async () => {
    const api = mockApi({ [`GET ${LIST}`]: [] })
    const { container } = renderPanel()

    await waitForCall(api, LIST)

    expect(container).toBeEmptyDOMElement()
  })

  it('lista nome, tamanho e skill, com link de download sem abrir no site', async () => {
    mockApi({ [`GET ${LIST}`]: [artifact('a', 'src/main.py')] })
    renderPanel()

    const item = (await screen.findByText('src/main.py')).closest('li') as HTMLElement

    expect(within(item).getByText(/2 KB/)).toBeInTheDocument()
    expect(within(item).getByText(/Skill de Impostos/)).toBeInTheDocument()
    const link = within(item).getByRole('link', { name: 'Baixar src/main.py' })
    expect(link).toHaveAttribute('href', '/api/v1/orchestrations/TRC-1/artifacts/a/download')
  })

  it('oferece baixar tudo em ZIP', async () => {
    mockApi({ [`GET ${LIST}`]: [artifact('a', 'a.py'), artifact('b', 'b.py')] })
    renderPanel()

    const link = await screen.findByRole('link', { name: /Baixar tudo/ })

    expect(link).toHaveAttribute('href', '/api/v1/orchestrations/TRC-1/artifacts.zip')
  })

  it('só busca o conteúdo ao pedir, e não busca de novo', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      [`GET ${LIST}`]: [artifact('a', 'a.py')],
      [`GET ${LIST}/a`]: { ...artifact('a', 'a.py'), content: "print('olá')" },
    })
    renderPanel()
    const show = await screen.findByRole('button', { name: 'Visualizar a.py' })
    expect(api.callsTo('GET', `${LIST}/a`)).toHaveLength(0)

    await user.click(show)
    expect(await screen.findByText("print('olá')")).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Ocultar a.py' }))
    expect(screen.queryByText("print('olá')")).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Visualizar a.py' }))

    expect(await screen.findByText("print('olá')")).toBeInTheDocument()
    expect(api.callsTo('GET', `${LIST}/a`)).toHaveLength(1)
  })

  it('mostra HTML como texto, sem executar', async () => {
    const user = userEvent.setup()
    const html = '<img src=x onerror="alert(1)">'
    mockApi({
      [`GET ${LIST}`]: [artifact('a', 'pagina.html')],
      [`GET ${LIST}/a`]: { ...artifact('a', 'pagina.html'), content: html },
    })
    const { container } = renderPanel()

    await user.click(await screen.findByRole('button', { name: 'Visualizar pagina.html' }))

    expect(await screen.findByText(html)).toBeInTheDocument()
    expect(container.querySelector('img')).toBeNull()
  })

  it('mostra o erro quando o conteúdo não carrega', async () => {
    const user = userEvent.setup()
    mockApi({
      [`GET ${LIST}`]: [artifact('a', 'a.py')],
      [`GET ${LIST}/a`]: apiError(404, 'Arquivo não encontrado.'),
    })
    renderPanel()

    await user.click(await screen.findByRole('button', { name: 'Visualizar a.py' }))

    expect(await screen.findByText('Arquivo não encontrado.')).toBeInTheDocument()
  })

  it('busca de novo quando uma pergunta gera novos arquivos', async () => {
    let files = [artifact('a', 'a.py')]
    mockApi({ [`GET ${LIST}`]: () => files })
    const { rerender } = renderPanel()
    await screen.findByText('a.py')

    files = [artifact('a', 'a.py'), artifact('b', 'b.py')]
    rerender(<ArtifactsPanel traceId="TRC-1" refreshKey={1} />)

    expect(await screen.findByText('b.py')).toBeInTheDocument()
  })

  it('não atrapalha a tela quando a lista falha', async () => {
    const api = mockApi({ [`GET ${LIST}`]: apiError(500, 'Erro interno.') })
    const { container } = renderPanel()

    await waitForCall(api, LIST)

    expect(container).toBeEmptyDOMElement()
  })
})

async function waitForCall(api: ReturnType<typeof mockApi>, path: string) {
  await waitFor(() => expect(api.callsTo('GET', path).length).toBeGreaterThan(0))
}

describe('ArtifactsPanel como material desenvolvido', () => {
  it('chama a seção de material desenvolvido e separa os arquivos por agente', async () => {
    mockApi({
      [`GET ${LIST}`]: [
        artifact('a', 'index.html', { agent_skill_name: 'Programação de Jogos Web' }),
        artifact('b', 'game.js', { agent_skill_name: 'Programação de Jogos Web' }),
        artifact('c', 'GDD.md', { agent_skill_name: 'Game Design' }),
      ],
    })
    renderPanel()

    expect(await screen.findByRole('heading', { name: 'Material desenvolvido (3 arquivos)' })).toBeInTheDocument()
    const code = screen.getByRole('group', { name: 'Programação de Jogos Web' })
    expect(within(code).getByText('index.html')).toBeInTheDocument()
    expect(within(code).getByText('game.js')).toBeInTheDocument()
    expect(within(screen.getByRole('group', { name: 'Game Design' })).getByText('GDD.md')).toBeInTheDocument()
  })
})
