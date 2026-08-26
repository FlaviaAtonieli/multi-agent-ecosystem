const API_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

export class ApiError extends Error {
  status: number
  requestId?: string
  details?: Array<{ field: string; message: string }>

  constructor(message: string, status: number, requestId?: string, details?: Array<{ field: string; message: string }>) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.requestId = requestId
    this.details = details
  }
}

function getCookie(name: string): string | undefined {
  const prefix = `${encodeURIComponent(name)}=`
  const cookie = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix))
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : undefined
}

async function prepareCsrf(): Promise<string> {
  const existing = getCookie('agenthub_csrf')
  if (existing) return existing

  const response = await fetch(`${API_URL}/auth/csrf`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) {
    throw new ApiError('Não foi possível preparar a sessão segura.', response.status)
  }

  const token = getCookie('agenthub_csrf')
  if (!token) {
    throw new ApiError('O navegador bloqueou o cookie de segurança.', 0)
  }
  return token
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const mutating = ['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)
  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')

  if (mutating) {
    headers.set('X-CSRF-Token', await prepareCsrf())
  }
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    method,
    headers,
    credentials: 'include',
  })

  if (response.status === 204) {
    return undefined as T
  }

  const payload = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(
      payload.message ?? 'Não foi possível concluir a operação.',
      response.status,
      payload.request_id,
      payload.details,
    )
  }
  return payload as T
}
