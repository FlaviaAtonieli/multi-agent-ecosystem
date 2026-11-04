import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { PublicRoute } from '../components/PublicRoute'
import { apiError, ApiResponse, mockApi, testUser } from '../test/api'
import { AuthProvider, useAuth } from './AuthContext'

function renderRoutes(start: string) {
  function Dashboard() {
    const { logout, user } = useAuth()
    return (
      <>
        <p>Painel de {user?.name}</p>
        <button onClick={() => logout().catch(() => undefined)}>Sair</button>
      </>
    )
  }

  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[start]}>
        <Routes>
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={<Dashboard />} />
          </Route>
          <Route element={<PublicRoute />}>
            <Route path="/login" element={<p>Tela de login</p>} />
          </Route>
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  )
}

describe('rotas protegidas', () => {
  it('manda para o login quem não tem sessão', async () => {
    mockApi({ 'GET /auth/me': apiError(401, 'Não autenticado.') })

    renderRoutes('/dashboard')

    expect(await screen.findByText('Tela de login')).toBeInTheDocument()
  })

  it('não mostra a tela protegida enquanto verifica a sessão', () => {
    mockApi({ 'GET /auth/me': testUser })

    renderRoutes('/dashboard')

    expect(screen.getByText('Preparando ambiente seguro…')).toBeInTheDocument()
    expect(screen.queryByText(/Painel de/)).not.toBeInTheDocument()
  })

  it('libera a tela protegida para quem tem sessão', async () => {
    mockApi({ 'GET /auth/me': testUser })

    renderRoutes('/dashboard')

    expect(await screen.findByText('Painel de Pessoa de Teste')).toBeInTheDocument()
  })

  it('tira do login quem já tem sessão', async () => {
    mockApi({ 'GET /auth/me': testUser })

    renderRoutes('/login')

    expect(await screen.findByText('Painel de Pessoa de Teste')).toBeInTheDocument()
  })

  it('trata falha do servidor como sem sessão, em vez de travar a tela', async () => {
    mockApi({ 'GET /auth/me': apiError(500, 'Erro interno.') })

    renderRoutes('/dashboard')

    expect(await screen.findByText('Tela de login')).toBeInTheDocument()
  })
})

describe('logout', () => {
  it('encerra a sessão no servidor e volta ao login', async () => {
    const user = userEvent.setup()
    const api = mockApi({ 'GET /auth/me': testUser, 'POST /auth/logout': new ApiResponse(204) })
    renderRoutes('/dashboard')

    await user.click(await screen.findByRole('button', { name: 'Sair' }))

    expect(await screen.findByText('Tela de login')).toBeInTheDocument()
    expect(api.callsTo('POST', '/auth/logout')).toHaveLength(1)
  })

  it('tira o usuário da tela mesmo se o servidor falhar', async () => {
    const user = userEvent.setup()
    mockApi({ 'GET /auth/me': testUser, 'POST /auth/logout': apiError(500, 'Erro interno.') })
    renderRoutes('/dashboard')

    await user.click(await screen.findByRole('button', { name: 'Sair' }))

    expect(await screen.findByText('Tela de login')).toBeInTheDocument()
  })
})

describe('useAuth', () => {
  it('avisa quando é usado fora do AuthProvider', () => {
    function Solto() {
      useAuth()
      return null
    }
    const originalError = console.error
    console.error = () => undefined

    expect(() => render(<Solto />)).toThrow('useAuth deve ser utilizado dentro de AuthProvider.')

    console.error = originalError
  })
})
