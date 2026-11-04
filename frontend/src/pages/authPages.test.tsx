import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ReactNode } from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { apiError, ApiResponse, authResponse, mockApi } from '../test/api'
import { ForgotPasswordPage } from './ForgotPasswordPage'
import { LoginPage } from './LoginPage'
import { RegisterPage } from './RegisterPage'
import { ResetPasswordPage } from './ResetPasswordPage'

const notLoggedIn = { 'GET /auth/me': apiError(401, 'Não autenticado.') }

function renderPage(page: ReactNode, path: string, start = path) {
  return render(
    <AuthProvider>
      <MemoryRouter initialEntries={[start]}>
        <Routes>
          <Route path={path} element={page} />
          <Route path="/dashboard" element={<p>Painel</p>} />
        </Routes>
      </MemoryRouter>
    </AuthProvider>,
  )
}

async function fillLogin(user: ReturnType<typeof userEvent.setup>) {
  await user.type(screen.getByPlaceholderText('voce@empresa.com'), 'pessoa@example.com')
  await user.type(screen.getByPlaceholderText('Sua senha'), 'Senha-Forte#123')
  await user.click(screen.getByRole('button', { name: 'Entrar' }))
}

describe('LoginPage', () => {
  it('entra e vai para o painel', async () => {
    const user = userEvent.setup()
    const api = mockApi({ ...notLoggedIn, 'POST /auth/login': authResponse })
    renderPage(<LoginPage />, '/login')

    await fillLogin(user)

    expect(await screen.findByText('Painel')).toBeInTheDocument()
    expect(api.jsonBody('POST', '/auth/login')).toEqual({ email: 'pessoa@example.com', password: 'Senha-Forte#123' })
  })

  it('mostra a recusa do backend e continua na tela de login', async () => {
    const user = userEvent.setup()
    mockApi({ ...notLoggedIn, 'POST /auth/login': apiError(401, 'E-mail ou senha inválidos.') })
    renderPage(<LoginPage />, '/login')

    await fillLogin(user)

    expect(await screen.findByText('E-mail ou senha inválidos.')).toBeInTheDocument()
    expect(screen.queryByText('Painel')).not.toBeInTheDocument()
  })

  it('traduz o erro vindo do login com GitHub', () => {
    mockApi(notLoggedIn)

    renderPage(<LoginPage />, '/login', '/login?error=github_email_in_use')

    expect(screen.getByText('Já existe uma conta com este e-mail. Entre com e-mail e senha.')).toBeInTheDocument()
  })

  describe('em navegador novo', () => {
    const challenge = new ApiResponse(202, { verification_required: true, email_hint: 'p***@example.com' })

    it('só entra depois de confirmar o código do e-mail', async () => {
      const user = userEvent.setup()
      const api = mockApi({ ...notLoggedIn, 'POST /auth/login': challenge, 'POST /auth/login/verify': authResponse })
      renderPage(<LoginPage />, '/login')

      await fillLogin(user)
      expect(await screen.findByText('p***@example.com')).toBeInTheDocument()
      expect(screen.queryByText('Painel')).not.toBeInTheDocument()

      await user.type(screen.getByPlaceholderText('000000'), '123456')
      await user.click(screen.getByRole('button', { name: /confirmar|validar|entrar/i }))

      expect(await screen.findByText('Painel')).toBeInTheDocument()
      expect(api.jsonBody('POST', '/auth/login/verify')).toEqual({ code: '123456' })
    })

    it('mantém a tela do código quando ele está errado', async () => {
      const user = userEvent.setup()
      mockApi({ ...notLoggedIn, 'POST /auth/login': challenge, 'POST /auth/login/verify': apiError(400, 'Código inválido.') })
      renderPage(<LoginPage />, '/login')

      await fillLogin(user)
      await user.type(await screen.findByPlaceholderText('000000'), '000000')
      await user.click(screen.getByRole('button', { name: /confirmar|validar|entrar/i }))

      expect(await screen.findByText('Código inválido.')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('000000')).toBeInTheDocument()
    })

    it('volta para a senha quando o desafio expirou', async () => {
      const user = userEvent.setup()
      mockApi({ ...notLoggedIn, 'POST /auth/login': challenge, 'POST /auth/login/verify': apiError(410, 'Código expirado.') })
      renderPage(<LoginPage />, '/login')

      await fillLogin(user)
      await user.type(await screen.findByPlaceholderText('000000'), '123456')
      await user.click(screen.getByRole('button', { name: /confirmar|validar|entrar/i }))

      expect(await screen.findByText('Código expirado.')).toBeInTheDocument()
      expect(screen.getByPlaceholderText('Sua senha')).toBeInTheDocument()
    })

    it('reenvia o código', async () => {
      const user = userEvent.setup()
      const api = mockApi({ ...notLoggedIn, 'POST /auth/login': challenge, 'POST /auth/login/resend': challenge })
      renderPage(<LoginPage />, '/login')

      await fillLogin(user)
      await user.click(await screen.findByRole('button', { name: /reenviar/i }))

      expect(await screen.findByText('Enviamos um novo código.')).toBeInTheDocument()
      expect(api.callsTo('POST', '/auth/login/resend')).toHaveLength(1)
    })
  })
})

describe('RegisterPage', () => {
  async function fillRegister(user: ReturnType<typeof userEvent.setup>, confirmation = 'Senha-Forte#123') {
    await user.type(screen.getByLabelText('Nome completo'), 'Pessoa de Teste')
    await user.type(screen.getByLabelText('E-mail'), 'pessoa@example.com')
    await user.type(screen.getByLabelText(/^Senha/), 'Senha-Forte#123')
    await user.type(screen.getByLabelText('Confirmar senha'), confirmation)
    await user.click(screen.getByRole('button', { name: 'Criar conta' }))
  }

  it('não chama o backend quando as senhas não coincidem', async () => {
    const user = userEvent.setup()
    const api = mockApi(notLoggedIn)
    renderPage(<RegisterPage />, '/register')

    await fillRegister(user, 'Outra-Senha#1234')

    expect(screen.getByText('As senhas informadas não coincidem.')).toBeInTheDocument()
    expect(api.callsTo('POST', '/auth/register')).toHaveLength(0)
  })

  it('cria a conta e já entra no painel', async () => {
    const user = userEvent.setup()
    const api = mockApi({ ...notLoggedIn, 'POST /auth/register': new ApiResponse(201, authResponse) })
    renderPage(<RegisterPage />, '/register')

    await fillRegister(user)

    expect(await screen.findByText('Painel')).toBeInTheDocument()
    expect(api.jsonBody('POST', '/auth/register')).toEqual({
      name: 'Pessoa de Teste',
      email: 'pessoa@example.com',
      password: 'Senha-Forte#123',
    })
  })

  it('mostra o motivo de cada campo recusado, e não só a mensagem geral', async () => {
    const user = userEvent.setup()
    mockApi({
      ...notLoggedIn,
      'POST /auth/register': apiError(422, 'Revise os dados informados.', [
        { field: 'password', message: 'A senha precisa de um caractere especial.' },
      ]),
    })
    renderPage(<RegisterPage />, '/register')

    await fillRegister(user)

    expect(await screen.findByText('A senha precisa de um caractere especial.')).toBeInTheDocument()
  })

  it('avisa quando o cadastro está desativado', async () => {
    const user = userEvent.setup()
    mockApi({ ...notLoggedIn, 'POST /auth/register': apiError(403, 'Novos cadastros estão desativados.') })
    renderPage(<RegisterPage />, '/register')

    await fillRegister(user)

    expect(await screen.findByText('Novos cadastros estão desativados.')).toBeInTheDocument()
  })
})

describe('ForgotPasswordPage', () => {
  it('confirma o pedido sem revelar se o e-mail existe', async () => {
    const user = userEvent.setup()
    const api = mockApi({
      ...notLoggedIn,
      'POST /auth/password/forgot': new ApiResponse(202, { message: 'Se o e-mail estiver cadastrado, você vai receber um link.' }),
    })
    renderPage(<ForgotPasswordPage />, '/forgot-password')

    await user.type(screen.getByLabelText('E-mail'), 'pessoa@example.com')
    await user.click(screen.getByRole('button', { name: 'Enviar link' }))

    expect(await screen.findByRole('status')).toHaveTextContent('Se o e-mail estiver cadastrado')
    expect(api.jsonBody('POST', '/auth/password/forgot')).toEqual({ email: 'pessoa@example.com' })
  })

  it('mostra o erro quando o e-mail não pôde ser enviado', async () => {
    const user = userEvent.setup()
    mockApi({ ...notLoggedIn, 'POST /auth/password/forgot': apiError(503, 'Não foi possível enviar o e-mail agora.') })
    renderPage(<ForgotPasswordPage />, '/forgot-password')

    await user.type(screen.getByLabelText('E-mail'), 'pessoa@example.com')
    await user.click(screen.getByRole('button', { name: 'Enviar link' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('Não foi possível enviar o e-mail agora.')
  })
})

describe('ResetPasswordPage', () => {
  const path = '/reset-password'

  async function fillReset(user: ReturnType<typeof userEvent.setup>, confirmation = 'Senha-Nova#12345') {
    await user.type(screen.getByLabelText(/^Nova senha/), 'Senha-Nova#12345')
    await user.type(screen.getByLabelText('Confirmar nova senha'), confirmation)
    await user.click(screen.getByRole('button', { name: 'Salvar nova senha' }))
  }

  it('não mostra o formulário quando o link vem sem token', () => {
    mockApi(notLoggedIn)

    renderPage(<ResetPasswordPage />, path)

    expect(screen.getByRole('alert')).toHaveTextContent('Link incompleto')
    expect(screen.queryByLabelText(/^Nova senha/)).not.toBeInTheDocument()
  })

  it('não chama o backend quando as senhas não conferem', async () => {
    const user = userEvent.setup()
    const api = mockApi(notLoggedIn)
    renderPage(<ResetPasswordPage />, path, `${path}?token=abc`)

    await fillReset(user, 'Outra-Senha#1234')

    expect(screen.getByRole('alert')).toHaveTextContent('As senhas não conferem.')
    expect(api.callsTo('POST', '/auth/password/reset')).toHaveLength(0)
  })

  it('envia o token do link junto com a senha nova', async () => {
    const user = userEvent.setup()
    const api = mockApi({ ...notLoggedIn, 'POST /auth/password/reset': new ApiResponse(204) })
    renderPage(<ResetPasswordPage />, path, `${path}?token=abc`)

    await fillReset(user)

    expect(await screen.findByRole('status')).toHaveTextContent('Senha redefinida')
    await waitFor(() => expect(api.jsonBody('POST', '/auth/password/reset')).toMatchObject({ token: 'abc' }))
  })

  it('avisa quando o link expirou', async () => {
    const user = userEvent.setup()
    mockApi({ ...notLoggedIn, 'POST /auth/password/reset': apiError(400, 'Link inválido ou expirado.') })
    renderPage(<ResetPasswordPage />, path, `${path}?token=velho`)

    await fillReset(user)

    expect(await screen.findByRole('alert')).toHaveTextContent('Link inválido ou expirado.')
  })
})
