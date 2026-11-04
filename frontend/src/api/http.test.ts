import { beforeEach, describe, expect, it, vi } from 'vitest'
import { apiError, ApiResponse, mockApi } from '../test/api'
import { ApiError, apiRequest } from './http'

describe('apiRequest', () => {
  it('não envia token CSRF em leitura', async () => {
    const api = mockApi({ 'GET /itens': [] })

    await apiRequest('/itens')

    expect(api.calls[0].headers.has('X-CSRF-Token')).toBe(false)
  })

  it('envia o token do cookie em toda operação que altera dados', async () => {
    const api = mockApi({ 'POST /itens': {}, 'DELETE /itens/1': new ApiResponse(204) })

    await apiRequest('/itens', { method: 'POST', body: '{}' })
    await apiRequest('/itens/1', { method: 'DELETE' })

    expect(api.calls.map((call) => call.headers.get('X-CSRF-Token'))).toEqual(['token-de-teste', 'token-de-teste'])
  })

  it('marca JSON, mas deixa o navegador definir o tipo de um upload', async () => {
    const api = mockApi({ 'POST /json': {}, 'POST /upload': {} })

    await apiRequest('/json', { method: 'POST', body: '{}' })
    await apiRequest('/upload', { method: 'POST', body: new FormData() })

    expect(api.calls[0].headers.get('Content-Type')).toBe('application/json')
    expect(api.calls[1].headers.has('Content-Type')).toBe(false)
  })

  it('devolve undefined em 204', async () => {
    mockApi({ 'DELETE /itens/1': new ApiResponse(204) })

    await expect(apiRequest('/itens/1', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('transforma a resposta de erro em ApiError com os detalhes do backend', async () => {
    const details = [{ field: 'email', message: 'E-mail inválido' }]
    mockApi({ 'POST /itens': apiError(422, 'Revise os dados informados.', details) })

    const error = await apiRequest('/itens', { method: 'POST' }).catch((caught) => caught)

    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ message: 'Revise os dados informados.', status: 422, requestId: 'req-teste', details })
  })

  it('usa uma mensagem padrão quando o erro não vem em JSON, como no limite do proxy', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('<html>504</html>', { status: 504 })))

    await expect(apiRequest('/itens')).rejects.toMatchObject({
      message: 'Não foi possível concluir a operação.',
      status: 504,
    })
  })
})

describe('preparação do CSRF', () => {
  beforeEach(() => {
    document.cookie = 'agenthub_csrf=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
  })

  it('busca o token antes da primeira operação, quando ainda não há cookie', async () => {
    const api = mockApi({
      'GET /auth/csrf': () => {
        document.cookie = 'agenthub_csrf=token-novo; path=/'
        return {}
      },
      'POST /itens': {},
    })

    await apiRequest('/itens', { method: 'POST' })

    expect(api.calls.map((call) => call.path)).toEqual(['/auth/csrf', '/itens'])
    expect(api.calls[1].headers.get('X-CSRF-Token')).toBe('token-novo')
  })

  it('avisa quando o navegador bloqueia o cookie, sem enviar a operação', async () => {
    const api = mockApi({ 'GET /auth/csrf': {}, 'POST /itens': {} })

    await expect(apiRequest('/itens', { method: 'POST' })).rejects.toThrow('O navegador bloqueou o cookie de segurança.')
    expect(api.callsTo('POST', '/itens')).toHaveLength(0)
  })

  it('não envia a operação quando o token não pode ser preparado', async () => {
    const api = mockApi({ 'GET /auth/csrf': apiError(503, 'fora do ar'), 'POST /itens': {} })

    await expect(apiRequest('/itens', { method: 'POST' })).rejects.toThrow('Não foi possível preparar a sessão segura.')
    expect(api.callsTo('POST', '/itens')).toHaveLength(0)
  })
})
