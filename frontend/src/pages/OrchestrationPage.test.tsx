import { act, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { RequestStatus } from '../api/orchestrationApi'
import { apiError, ApiResponse, mockApi } from '../test/api'
import { OrchestrationPage } from './OrchestrationPage'

const ORCHESTRATION = '/orchestrations/TRC-1'
const START = '/agent-skills/requests/req-1/start'
const ASK = '/agent-skills/requests/req-1/ask/start'

const consolidated = {
  id: 'cons-1',
  trace_id: 'TRC-1',
  technical_synthesis: '[Contabilidade] Impacto fiscal baixo.',
  recommendations: ['Revisar a alíquota'],
  risks: ['Multa por atraso'],
  limitations: [],
  participating_agents: ['Skill de Impostos'],
  overall_confidence_level: 'ALTO',
  quality_gate_approved: true,
  requires_human_review: false,
  invocation_ids: [],
  created_at: '2026-11-03T12:00:00Z',
}

const skillResult = {
  id: 'inv-1',
  agent_skill_name: 'Skill de Impostos',
  status: 'COMPLETED',
  confidence_level: 'ALTO',
  created_at: '2026-11-03T12:00:00Z',
  result: {
    trace_id: 'TRC-1',
    agente_emissor: { nome: 'Skill de Impostos', versao_prompt: null, dominio: 'Contabilidade' },
    analise_estruturada: { resumo_executivo: 'Resumo.', descobertas_tecnicas: [], impactos_mapeados: [] },
    governanca: { nivel_confianca: 'ALTO', justificativa_confianca: 'Boas fontes.', referencias_catalogo: [] },
  },
}

function event(sequence_number: number, event_type: string, payload: Record<string, unknown> = {}, message = '') {
  return {
    id: `evt-${sequence_number}`,
    sequence_number,
    event_type,
    actor: 'Orquestrador',
    title: `Evento ${event_type}`,
    message,
    payload,
    created_at: new Date().toISOString(),
  }
}

function detail(status: RequestStatus, options: { result?: boolean; events?: ReturnType<typeof event>[] } = {}) {
  return {
    technical_request: {
      id: 'req-1',
      trace_id: 'TRC-1',
      title: 'Reduzir o tempo do job',
      problem: 'O job demora.',
      objective: 'Reduzir o tempo.',
      context: status === 'CANCELLED' ? 'Contexto da solicitação.' : null,
      restrictions: [],
      requested_domains: [],
      status,
      created_at: '2026-11-03T12:00:00Z',
      updated_at: '2026-11-03T12:00:00Z',
      consolidated_response: options.result ? consolidated : null,
    },
    run: { id: 'run-1', status, current_stage: 'etapa', started_at: null, completed_at: null, created_at: '', updated_at: '' },
    events: options.events ?? [],
  }
}

const llmStatus = {
  model: 'openai/gpt-5-mini',
  allowed_models: ['openai/gpt-5-mini', 'outro/modelo'],
  daily_token_limit_per_user: 0,
  tokens_used_today: 0,
}

const commonRoutes = {
  'GET /llm/status': llmStatus,
  'GET /requests/req-1/attachments': [],
  'GET /orchestrations/TRC-1/skill-results': [skillResult],
  'GET /orchestrations/TRC-1/follow-ups': [],
  'GET /orchestrations/TRC-1/artifacts': [],
}

function renderPage(state?: unknown) {
  return render(
    <MemoryRouter initialEntries={[{ pathname: ORCHESTRATION, state }]}>
      <Routes>
        <Route path="/orchestrations/:traceId" element={<OrchestrationPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

// A página consulta o backend a cada 4 s enquanto a execução roda.
async function nextPoll() {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(4000)
  })
}

describe('OrchestrationPage', () => {
  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  const setupUser = () => userEvent.setup({ advanceTimers: vi.advanceTimersByTime })

  it('avisa quando a orquestração não pode ser carregada', async () => {
    mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: apiError(404, 'Orquestração não encontrada.') })

    renderPage()

    expect(await screen.findByText('Orquestração não encontrada.')).toBeInTheDocument()
  })

  it('avisa, depois de criar a solicitação, quais anexos falharam', async () => {
    mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: detail('QUALIFIED') })

    renderPage({ failedAttachmentUploads: ['a.txt'] })

    expect(await screen.findByText(/Não foi possível anexar: a\.txt/)).toBeInTheDocument()
  })

  it('inicia a execução em segundo plano, sem esperar o resultado na mesma chamada', async () => {
    const user = setupUser()
    let status: RequestStatus = 'QUALIFIED'
    const api = mockApi({
      ...commonRoutes,
      [`GET ${ORCHESTRATION}`]: () => detail(status),
      [`POST ${START}`]: () => {
        status = 'RUNNING'
        return new ApiResponse(202, { trace_id: 'TRC-1', status: 'RUNNING' })
      },
    })
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Executar orquestração' }))

    expect(await screen.findByText('Processando orquestração')).toBeInTheDocument()
    expect(api.jsonBody('POST', START)).toEqual({ model: 'openai/gpt-5-mini' })
    expect(api.callsTo('POST', '/agent-skills/requests/req-1/execute')).toHaveLength(0)
  })

  it('envia o modelo escolhido', async () => {
    const user = setupUser()
    const api = mockApi({
      ...commonRoutes,
      [`GET ${ORCHESTRATION}`]: detail('QUALIFIED'),
      [`POST ${START}`]: new ApiResponse(202, {}),
    })
    renderPage()

    await user.selectOptions(await screen.findByLabelText(/Modelo de IA/), await screen.findByRole('option', { name: 'outro/modelo' }))
    await user.click(screen.getByRole('button', { name: 'Executar orquestração' }))

    await waitFor(() => expect(api.jsonBody('POST', START)).toEqual({ model: 'outro/modelo' }))
  })

  it('mostra o motivo quando a execução é recusada, como em clique duplo', async () => {
    const user = setupUser()
    mockApi({
      ...commonRoutes,
      [`GET ${ORCHESTRATION}`]: detail('QUALIFIED'),
      [`POST ${START}`]: apiError(409, 'A orquestração já está em execução.'),
    })
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Executar orquestração' }))

    expect(await screen.findByText('A orquestração já está em execução.')).toBeInTheDocument()
  })

  it('bloqueia a execução quando a cota diária de tokens acabou', async () => {
    mockApi({
      ...commonRoutes,
      'GET /llm/status': { ...llmStatus, daily_token_limit_per_user: 100, tokens_used_today: 100 },
      [`GET ${ORCHESTRATION}`]: detail('QUALIFIED'),
    })
    renderPage()

    await waitFor(async () => expect(await screen.findByRole('button', { name: 'Executar orquestração' })).toBeDisabled())
  })

  it('acompanha a execução e mostra o resultado sozinho, sem recarregar', async () => {
    let current = detail('RUNNING', { events: [event(1, 'ORCHESTRATION_EXECUTION_STARTED', { max_parallel: 3 })] })
    mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: () => current })
    renderPage()
    expect(await screen.findByText('Processando orquestração')).toBeInTheDocument()
    expect(screen.queryByText('Resposta consolidada')).not.toBeInTheDocument()

    current = detail('COMPLETED', { result: true })
    await nextPoll()

    expect(await screen.findByText('Resposta consolidada')).toBeInTheDocument()
    expect(screen.queryByText('Processando orquestração')).not.toBeInTheDocument()
    expect(screen.getByText('Orquestração executada e aprovada pelo Quality Gate.')).toBeInTheDocument()
    expect(screen.getByText('Impacto fiscal baixo.')).toBeInTheDocument()
    expect(await screen.findByText('Skill de Impostos')).toBeInTheDocument()
  })

  it('mostra os arquivos gerados junto com o resultado', async () => {
    mockApi({
      ...commonRoutes,
      [`GET ${ORCHESTRATION}`]: detail('COMPLETED', { result: true }),
      'GET /orchestrations/TRC-1/artifacts': [
        { id: 'a', filename: 'src/main.py', size_bytes: 10, agent_skill_name: 'Skill', domain: 'd', created_at: '' },
      ],
    })

    renderPage()

    expect(await screen.findByText('src/main.py')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Baixar tudo/ })).toBeInTheDocument()
  })

  it('não interrompe o acompanhamento por uma falha pontual de rede', async () => {
    let response: unknown = detail('RUNNING')
    mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: () => response })
    renderPage()
    await screen.findByText('Processando orquestração')

    response = apiError(504, 'Tempo esgotado.')
    await nextPoll()
    expect(screen.getByText('Processando orquestração')).toBeInTheDocument()

    response = detail('COMPLETED', { result: true })
    await nextPoll()

    expect(await screen.findByText('Resposta consolidada')).toBeInTheDocument()
  })

  it('para de consultar o backend quando a execução termina', async () => {
    let current = detail('RUNNING')
    const api = mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: () => current })
    renderPage()
    await screen.findByText('Processando orquestração')
    current = detail('COMPLETED', { result: true })
    await nextPoll()
    await screen.findByText('Resposta consolidada')

    const before = api.callsTo('GET', ORCHESTRATION).length
    await nextPoll()
    await nextPoll()

    expect(api.callsTo('GET', ORCHESTRATION)).toHaveLength(before)
  })

  it('quando a execução falha, explica e oferece executar de novo', async () => {
    let current = detail('RUNNING')
    mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: () => current })
    renderPage()
    await screen.findByText('Processando orquestração')

    current = detail('FAILED')
    await nextPoll()

    expect(await screen.findByText(/A execução foi interrompida/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Executar novamente' })).toBeEnabled()
  })

  describe('interromper a execução', () => {
    const CANCEL = '/agent-skills/requests/req-1/cancel'

    it('pede confirmação antes de interromper', async () => {
      const user = setupUser()
      const api = mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: detail('RUNNING') })
      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Interromper execução' }))
      await user.click(screen.getByRole('button', { name: 'Continuar executando' }))

      expect(api.callsTo('POST', CANCEL)).toHaveLength(0)
      expect(screen.getByRole('button', { name: 'Interromper execução' })).toBeInTheDocument()
    })

    it('interrompe e oferece completar o contexto, já preenchido, para executar de novo', async () => {
      const user = setupUser()
      let current = detail('RUNNING')
      const api = mockApi({
        ...commonRoutes,
        [`GET ${ORCHESTRATION}`]: () => current,
        [`POST ${CANCEL}`]: () => {
          current = detail('CANCELLED')
          return new ApiResponse(202, { trace_id: 'TRC-1', status: 'CANCELLING' })
        },
      })
      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Interromper execução' }))
      await user.click(screen.getByRole('button', { name: 'Confirmar interrupção' }))

      expect(await screen.findByText(/Você interrompeu a execução/)).toBeInTheDocument()
      expect(api.callsTo('POST', CANCEL)).toHaveLength(1)
      expect(screen.queryByText('Processando orquestração')).not.toBeInTheDocument()
      expect(screen.getByLabelText('Complementar contexto')).toHaveValue('Contexto da solicitação.')
      expect(screen.getByRole('button', { name: 'Executar novamente' })).toBeEnabled()
    })

    it('mostra o motivo quando não dá para interromper', async () => {
      const user = setupUser()
      mockApi({
        ...commonRoutes,
        [`GET ${ORCHESTRATION}`]: detail('RUNNING'),
        [`POST ${CANCEL}`]: apiError(409, 'A solicitação não está em execução.'),
      })
      renderPage()

      await user.click(await screen.findByRole('button', { name: 'Interromper execução' }))
      await user.click(screen.getByRole('button', { name: 'Confirmar interrupção' }))

      expect(await screen.findByText('A solicitação não está em execução.')).toBeInTheDocument()
    })
  })

  it('avisa quando o resultado aguarda revisão humana', async () => {
    let current = detail('RUNNING')
    mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: () => current })
    renderPage()
    await screen.findByText('Processando orquestração')

    current = detail('VALIDATING', { result: true })
    await nextPoll()

    expect(await screen.findByText('Orquestração executada. O resultado aguarda revisão humana.')).toBeInTheDocument()
  })

  it('complementa o contexto de uma solicitação incompleta', async () => {
    const user = setupUser()
    let status: RequestStatus = 'AWAITING_CONTEXT'
    const api = mockApi({
      ...commonRoutes,
      [`GET ${ORCHESTRATION}`]: () => detail(status),
      'POST /requests/req-1/context': () => {
        status = 'QUALIFIED'
        return {}
      },
    })
    renderPage()

    await user.type(await screen.findByLabelText('Complementar contexto'), 'Sistema legado em Java.')
    await user.click(screen.getByRole('button', { name: 'Enviar complementação' }))

    expect(await screen.findByText('Contexto complementado com sucesso.')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Executar orquestração' })).toBeInTheDocument()
    expect(api.jsonBody('POST', '/requests/req-1/context')).toEqual({ context: 'Sistema legado em Java.' })
  })

  describe('perguntas de acompanhamento', () => {
    const asked = event(1, 'FOLLOW_UP_QUESTION_ASKED')

    it('envia a pergunta em segundo plano e bloqueia outra enquanto responde', async () => {
      const user = setupUser()
      let current = detail('COMPLETED', { result: true })
      const api = mockApi({
        ...commonRoutes,
        [`GET ${ORCHESTRATION}`]: () => current,
        [`POST ${ASK}`]: () => {
          current = detail('COMPLETED', { result: true, events: [asked] })
          return new ApiResponse(202, {})
        },
      })
      renderPage()

      await user.type(await screen.findByLabelText('Pergunta de acompanhamento'), 'Qual é o risco?')
      await user.click(screen.getByRole('button', { name: 'Perguntar' }))

      expect(await screen.findByText('Os agentes estão respondendo.')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Perguntando…' })).toBeDisabled()
      expect(api.jsonBody('POST', ASK)).toEqual({ question: 'Qual é o risco?', target_domain: null, model: 'openai/gpt-5-mini' })
    })

    it('mostra a resposta quando ela fica pronta, sem recarregar', async () => {
      let current = detail('COMPLETED', { result: true, events: [asked] })
      let followUps: unknown[] = []
      mockApi({
        ...commonRoutes,
        [`GET ${ORCHESTRATION}`]: () => current,
        'GET /orchestrations/TRC-1/follow-ups': () => followUps,
      })
      renderPage()
      await screen.findByText('Os agentes estão respondendo.')

      current = detail('COMPLETED', { result: true, events: [asked, event(2, 'FOLLOW_UP_RESPONSE_RECEIVED')] })
      followUps = [
        {
          id: 'f-1',
          sequence_number: 1,
          question: 'Qual é o risco?',
          target_domain: null,
          synthesis: 'O risco é baixo.',
          results: [],
          overall_confidence_level: 'ALTO',
          quality_gate_approved: true,
          requires_human_review: false,
          created_at: '2026-11-03T12:00:00Z',
        },
      ]
      await nextPoll()

      expect(await screen.findByText('Qual é o risco?')).toBeInTheDocument()
      expect(screen.queryByText('Os agentes estão respondendo.')).not.toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Perguntar' })).toBeEnabled()
    })

    it('mostra o erro quando a pergunta falha em segundo plano', async () => {
      let current = detail('COMPLETED', { result: true, events: [asked] })
      mockApi({ ...commonRoutes, [`GET ${ORCHESTRATION}`]: () => current })
      renderPage()
      await screen.findByText('Os agentes estão respondendo.')

      current = detail('COMPLETED', {
        result: true,
        events: [asked, event(2, 'FOLLOW_UP_FAILED', {}, 'Os agentes não responderam.')],
      })
      await nextPoll()

      expect(await screen.findByText('Os agentes não responderam.')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Perguntar' })).toBeEnabled()
    })

    it('não trata como pendente uma pergunta que já foi respondida', async () => {
      mockApi({
        ...commonRoutes,
        [`GET ${ORCHESTRATION}`]: detail('COMPLETED', { result: true, events: [asked, event(2, 'FOLLOW_UP_RESPONSE_RECEIVED')] }),
      })
      renderPage()

      expect(await screen.findByRole('button', { name: 'Perguntar' })).toBeEnabled()
    })
  })
})
