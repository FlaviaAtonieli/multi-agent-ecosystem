import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { apiError, ApiResponse, mockApi } from '../test/api'
import { NewRequestPage } from './NewRequestPage'

const created = new ApiResponse(201, { id: 'req-1', trace_id: 'TRC-1' })
const skills = ['codigo_legado', 'regras_negocio', 'seguranca_informacao', 'Contabilidade'].map((domain, index) => ({
  id: `skill-${index}`,
  domain,
  enabled: true,
  status: 'approved',
}))
const clan = { id: 'clan-1', name: 'Meu comitê', is_open: false }
const otherClan = { id: 'clan-2', name: 'Outro comitê', is_open: false }
const openClan = { id: 'clan-open', name: 'Ecossistema', is_open: true }
const closedClan = { id: 'clan-closed', name: 'Comitê fechado', is_open: false }
const baseRoutes = {
  'GET /clans?mine=true': [clan],
  'GET /clans': [clan, openClan, closedClan],
  'GET /clans/clan-1/skills': skills,
}

function Destination() {
  const location = useLocation()
  return <p>Orquestração {JSON.stringify(location.state)}</p>
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/requests/new']}>
      <Routes>
        <Route path="/requests/new" element={<NewRequestPage />} />
        <Route path="/orchestrations/:traceId" element={<Destination />} />
      </Routes>
    </MemoryRouter>,
  )
}

type User = ReturnType<typeof userEvent.setup>
const next = (user: User) => user.click(screen.getByRole('button', { name: 'Continuar →' }))

async function goToLastStep(user: User) {
  await user.type(screen.getByPlaceholderText(/^Ex\.: Erro de timeout/), 'Reduzir o tempo do job')
  await next(user)
  await user.type(screen.getByPlaceholderText(/^Descreva o comportamento/), 'O job demora mais a cada mês.')
  await user.type(screen.getByPlaceholderText(/^Informe qual resposta/), 'Reduzir o tempo.')
  await next(user)
}

const submit = (user: User) => user.click(screen.getByRole('button', { name: 'Registrar e gerar Trace ID' }))

describe('NewRequestPage', () => {
  it('não avança com título curto demais', async () => {
    const user = userEvent.setup()
    mockApi(baseRoutes)
    renderPage()

    await user.type(screen.getByPlaceholderText(/^Ex\.: Erro de timeout/), 'abc')
    await next(user)

    expect(screen.getByText('Informe um título com pelo menos 5 caracteres.')).toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/^Descreva o comportamento/)).not.toBeInTheDocument()
  })

  it('não avança sem problema e objetivo', async () => {
    const user = userEvent.setup()
    mockApi(baseRoutes)
    renderPage()

    await user.type(screen.getByPlaceholderText(/^Ex\.: Erro de timeout/), 'Título válido')
    await next(user)
    await next(user)

    expect(screen.getByText(/Descreva o problema \(mín\. 10 caracteres\)/)).toBeInTheDocument()
  })

  it('sem escolha de agentes, avisa que todos vão analisar e envia a lista vazia', async () => {
    const user = userEvent.setup()
    const api = mockApi({ ...baseRoutes, 'POST /requests': created })
    renderPage()
    await goToLastStep(user)

    expect(await screen.findByText(/todos os 4 agentes vão analisar, cerca de 2 min/)).toBeInTheDocument()
    await submit(user)

    expect(await screen.findByText(/^Orquestração/)).toBeInTheDocument()
    expect(api.jsonBody('POST', '/requests')).toMatchObject({
      title: 'Reduzir o tempo do job',
      problem: 'O job demora mais a cada mês.',
      objective: 'Reduzir o tempo.',
      requested_domains: [],
    })
  })

  it('envia só os agentes escolhidos e atualiza a estimativa, inclusive com área livre', async () => {
    const user = userEvent.setup()
    const api = mockApi({ ...baseRoutes, 'POST /requests': created })
    renderPage()
    await goToLastStep(user)

    await user.click(await screen.findByRole('button', { name: 'Contabilidade' }))
    await user.click(screen.getByRole('button', { name: 'Código Legado' }))
    expect(screen.getByText('2 agentes escolhidos: menos de 1 min.')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Código Legado' }))
    expect(screen.getByRole('button', { name: 'Código Legado' })).toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByText('1 agente escolhido: menos de 1 min.')).toBeInTheDocument()

    await submit(user)
    await screen.findByText(/^Orquestração/)

    expect(api.jsonBody('POST', '/requests').requested_domains).toEqual(['Contabilidade'])
  })

  it('mostra o motivo quando o servidor recusa o problema', async () => {
    const user = userEvent.setup()
    const reason = 'Descreva o problema com palavras que expliquem a situação, sem repetições como "TESTE TESTE".'
    mockApi({
      ...baseRoutes,
      'POST /requests': apiError(422, 'Revise os dados informados.', [{ field: 'problem', message: reason }]),
    })
    renderPage()
    await goToLastStep(user)
    await submit(user)

    expect(await screen.findByText(reason)).toBeInTheDocument()
  })

  it('continua funcionando quando o catálogo não carrega', async () => {
    const user = userEvent.setup()
    mockApi({
      ...baseRoutes,
      'GET /clans/clan-1/skills': apiError(500, 'Erro interno.'),
      'POST /requests': created,
    })
    renderPage()
    await goToLastStep(user)
    await screen.findByRole('combobox', { name: 'Comitê que vai responder' })

    await submit(user)

    expect(await screen.findByText(/^Orquestração/)).toBeInTheDocument()
  })

  describe('comitê da solicitação', () => {
    it('com um comitê só, já o seleciona e o envia', async () => {
      const user = userEvent.setup()
      const api = mockApi({ ...baseRoutes, 'POST /requests': created })
      renderPage()
      await goToLastStep(user)
      await screen.findByRole('button', { name: 'Contabilidade' })

      await submit(user)
      await screen.findByText(/^Orquestração/)

      expect(api.jsonBody('POST', '/requests').clan_id).toBe('clan-1')
    })

    it('com vários comitês, exige escolher antes de registrar', async () => {
      const user = userEvent.setup()
      const api = mockApi({
        ...baseRoutes,
        'GET /clans?mine=true': [clan, otherClan],
        'POST /requests': created,
      })
      renderPage()
      await goToLastStep(user)
      await screen.findByRole('option', { name: 'Outro comitê' })

      await submit(user)

      expect(screen.getByText('Escolha o comitê que vai responder.')).toBeInTheDocument()
      expect(api.callsTo('POST', '/requests')).toHaveLength(0)

      await user.selectOptions(screen.getByRole('combobox', { name: 'Comitê que vai responder' }), 'clan-1')

      expect(screen.queryByText('Escolha o comitê que vai responder.')).not.toBeInTheDocument()
    })

    it('mostra só os agentes do comitê escolhido e limpa a escolha ao trocar', async () => {
      const user = userEvent.setup()
      const api = mockApi({
        ...baseRoutes,
        'GET /clans?mine=true': [clan, otherClan],
        'GET /clans/clan-2/skills': [{ id: 's', domain: 'apis_integracoes', enabled: true, status: 'approved' }],
        'POST /requests': created,
      })
      renderPage()
      await goToLastStep(user)
      const select = await screen.findByRole('combobox', { name: 'Comitê que vai responder' })
      await screen.findByRole('option', { name: 'Outro comitê' })

      await user.selectOptions(select, 'clan-1')
      await user.click(await screen.findByRole('button', { name: 'Contabilidade' }))
      await user.selectOptions(select, 'clan-2')
      await screen.findByRole('button', { name: 'APIs e Integrações' })

      expect(screen.queryByRole('button', { name: 'Contabilidade' })).not.toBeInTheDocument()
      await submit(user)
      await screen.findByText(/^Orquestração/)
      expect(api.jsonBody('POST', '/requests')).toMatchObject({ clan_id: 'clan-2', requested_domains: [] })
    })

    it('ignora skills desativadas do comitê', async () => {
      const user = userEvent.setup()
      mockApi({
        ...baseRoutes,
        'GET /clans/clan-1/skills': [
          { id: 'a', domain: 'codigo_legado', enabled: true, status: 'approved' },
          { id: 'b', domain: 'Contabilidade', enabled: false, status: 'approved' },
        ],
      })
      renderPage()
      await goToLastStep(user)

      await screen.findByRole('button', { name: 'Código Legado' })
      expect(screen.queryByRole('button', { name: 'Contabilidade' })).not.toBeInTheDocument()
    })

    it('skill adicionada pela sugestão passa a ser um agente do comitê', async () => {
      const user = userEvent.setup()
      mockApi({
        ...baseRoutes,
        'GET /clans/clan-1/skills': [skills[0]],
        'POST /agent-skills/suggestions': {
          available: true,
          suggestions: [{ id: 'novo', name: 'Skill Nova', domain: 'Jurídico', objective: 'Objetivo.', score: 0.5 }],
          best_clan_score: 0.1,
          covered_by_clan: false,
          catalog_gap: false,
          can_add_to_clan: true,
        },
        'POST /clans/clan-1/skills': new ApiResponse(201, {}),
      })
      renderPage()
      await goToLastStep(user)
      await screen.findByRole('button', { name: 'Código Legado' })

      await user.click(screen.getByRole('button', { name: 'Verificar skills que podem ajudar' }))
      await user.click(await screen.findByRole('button', { name: 'Adicionar Skill Nova ao comitê' }))

      expect(await screen.findByRole('button', { name: 'Jurídico' })).toBeInTheDocument()
    })

    it('não deixa registrar com um comitê sem skills ativas', async () => {
      const user = userEvent.setup()
      const api = mockApi({ ...baseRoutes, 'GET /clans/clan-1/skills': [], 'POST /requests': created })
      renderPage()
      await goToLastStep(user)
      await screen.findByText(/ainda não tem Agent Skills ativas/)

      await submit(user)

      expect(screen.getByText('Este comitê ainda não tem Agent Skills ativas. Escolha outro ou adicione skills a ele.', { selector: '.alert' })).toBeInTheDocument()
      expect(api.callsTo('POST', '/requests')).toHaveLength(0)
    })

    it('sem comitê, oferece entrar em um comitê aberto e passa a usá-lo', async () => {
      const user = userEvent.setup()
      const api = mockApi({
        ...baseRoutes,
        'GET /clans?mine=true': [],
        'GET /clans': [openClan, closedClan],
        'POST /clans/clan-open/join': {},
        'GET /clans/clan-open/skills': skills,
        'POST /requests': created,
      })
      renderPage()
      await goToLastStep(user)

      expect(screen.queryByRole('button', { name: 'Entrar em Comitê fechado' })).not.toBeInTheDocument()
      await user.click(await screen.findByRole('button', { name: 'Entrar em Ecossistema' }))
      await screen.findByRole('button', { name: 'Contabilidade' })
      await submit(user)
      await screen.findByText(/^Orquestração/)

      expect(api.callsTo('POST', '/clans/clan-open/join')).toHaveLength(1)
      expect(api.jsonBody('POST', '/requests').clan_id).toBe('clan-open')
    })

    it('sem comitê, não registra a solicitação', async () => {
      const user = userEvent.setup()
      const api = mockApi({ 'GET /clans?mine=true': [], 'GET /clans': [], 'POST /requests': created })
      renderPage()
      await goToLastStep(user)
      await screen.findByRole('link', { name: 'Criar um comitê' })

      await submit(user)

      expect(api.callsTo('POST', '/requests')).toHaveLength(0)
    })
  })

  it('adiciona restrição sem repetir e permite remover', async () => {
    const user = userEvent.setup()
    const api = mockApi({ ...baseRoutes, 'POST /requests': created })
    renderPage()
    await goToLastStep(user)
    const input = screen.getByPlaceholderText('+ Adicionar restrição')

    await user.type(input, 'Sem parar o serviço{Enter}')
    await user.type(input, 'Sem parar o serviço{Enter}')
    await user.click(screen.getByRole('button', { name: 'Remover restrição Não executar alterações automaticamente' }))
    await submit(user)
    await screen.findByText(/^Orquestração/)

    expect(api.jsonBody('POST', '/requests').restrictions).toEqual(['Sem parar o serviço'])
  })

  it('recusa anexo grande demais e mantém os outros', async () => {
    const user = userEvent.setup()
    mockApi(baseRoutes)
    const { container } = renderPage()
    await goToLastStep(user)
    const input = container.querySelector<HTMLInputElement>('input[type="file"]')!

    await user.upload(input, [
      new File(['x'.repeat(300_001)], 'grande.txt', { type: 'text/plain' }),
      new File(['ok'], 'pequeno.txt', { type: 'text/plain' }),
    ])

    expect(screen.getByText('grande.txt excede 300 KB e não foi adicionado.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remover anexo pequeno.txt' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Remover anexo grande.txt' })).not.toBeInTheDocument()
  })

  it('não perde a solicitação quando um anexo falha: avisa na tela seguinte', async () => {
    const user = userEvent.setup()
    mockApi({
      ...baseRoutes,
      'POST /requests': created,
      'POST /requests/req-1/attachments': apiError(415, 'Tipo não aceito.'),
    })
    const { container } = renderPage()
    await goToLastStep(user)
    await user.upload(container.querySelector<HTMLInputElement>('input[type="file"]')!, new File(['ok'], 'a.txt', { type: 'text/plain' }))

    await submit(user)

    expect(await screen.findByText(/^Orquestração/)).toHaveTextContent('{"failedAttachmentUploads":["a.txt"]}')
  })

  it('fica na tela e mostra o erro quando a solicitação é recusada', async () => {
    const user = userEvent.setup()
    mockApi({ ...baseRoutes, 'POST /requests': apiError(429, 'Muitas solicitações.') })
    renderPage()
    await goToLastStep(user)

    await submit(user)

    expect(await screen.findByText('Muitas solicitações.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Registrar e gerar Trace ID' })).toBeEnabled()
  })
})
