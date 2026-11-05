import { vi } from 'vitest'

type RouteResult = { status: number; body?: unknown } | unknown
type RouteHandler = RouteResult | ((call: RecordedCall) => RouteResult)

export type RecordedCall = {
  method: string
  path: string
  headers: Headers
  body: BodyInit | null | undefined
}

export class ApiResponse {
  constructor(
    readonly status: number,
    readonly body?: unknown,
  ) {}
}

export function apiError(status: number, message: string, details?: Array<{ field: string; message: string }>) {
  return new ApiResponse(status, { message, details, request_id: 'req-teste' })
}

// Troca só a chamada de rede: o código de verdade (telas, contexto de login,
// módulos de API e http.ts) roda inteiro, como no navegador. Rota sem resposta
// devolve 404, então um caminho errado no código faz o teste falhar.
export function mockApi(routes: Record<string, RouteHandler>) {
  const calls: RecordedCall[] = []

  vi.stubGlobal(
    'fetch',
    vi.fn(async (url: string, init: RequestInit = {}) => {
      const path = url.replace('/api/v1', '')
      const call = {
        method: init.method ?? 'GET',
        path,
        headers: new Headers(init.headers),
        body: init.body,
      }
      calls.push(call)

      const route = routes[`${call.method} ${path}`]
      const resolved = typeof route === 'function' ? (route as (call: RecordedCall) => RouteResult)(call) : route
      if (resolved === undefined) {
        return new Response(JSON.stringify({ message: `Rota sem resposta no teste: ${call.method} ${path}` }), {
          status: 404,
        })
      }

      const { status, body } = resolved instanceof ApiResponse ? resolved : { status: 200, body: resolved }
      return new Response(status === 204 ? null : JSON.stringify(body), { status })
    }),
  )

  return {
    calls,
    callsTo: (method: string, path: string) => calls.filter((call) => call.method === method && call.path === path),
    jsonBody: (method: string, path: string) => {
      const call = calls.find((item) => item.method === method && item.path === path)
      return JSON.parse(String(call?.body))
    },
  }
}

export const testUser = {
  id: 'user-1',
  name: 'Pessoa de Teste',
  email: 'pessoa@example.com',
  is_active: true,
  avatar_url: null,
  created_at: '2026-11-01T00:00:00Z',
  onboarding_completed_at: '2026-11-01T00:00:00Z',
  has_password: true,
  oauth_provider: null,
  is_initial_account: false,
}

export const authResponse = { user: testUser, session_expires_at: '2026-11-02T00:00:00Z' }
