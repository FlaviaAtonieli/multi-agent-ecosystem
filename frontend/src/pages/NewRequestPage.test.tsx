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
}))
const baseRoutes = { 'GET /agent-skills?only_active=true': skills }

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

  it('continua funcionando quando o catálogo não carrega', async () => {
    const user = userEvent.setup()
    mockApi({ 'GET /agent-skills?only_active=true': apiError(500, 'Erro interno.'), 'POST /requests': created })
    renderPage()
    await goToLastStep(user)

    await submit(user)

    expect(await screen.findByText(/^Orquestração/)).toBeInTheDocument()
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
