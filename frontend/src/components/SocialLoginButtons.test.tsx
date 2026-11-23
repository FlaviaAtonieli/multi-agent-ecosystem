import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { apiError, mockApi } from '../test/api'
import { SocialLoginButtons } from './SocialLoginButtons'

describe('SocialLoginButtons', () => {
  it('mostra só os logins ligados', async () => {
    mockApi({ 'GET /auth/providers': { github: true, google: false } })
    render(<SocialLoginButtons />)

    expect(await screen.findByRole('link', { name: /Continuar com GitHub/ })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: /Continuar com Google/ })).not.toBeInTheDocument()
    expect(screen.getByText('ou')).toBeInTheDocument()
  })

  it('com os dois ligados, mostra os dois', async () => {
    mockApi({ 'GET /auth/providers': { github: true, google: true } })
    render(<SocialLoginButtons />)

    expect(await screen.findByRole('link', { name: /Continuar com Google/ })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Continuar com GitHub/ })).toBeInTheDocument()
  })

  it('sem nenhum ligado, não mostra nada, nem o "ou"', async () => {
    const api = mockApi({ 'GET /auth/providers': { github: false, google: false } })
    const { container } = render(<SocialLoginButtons />)

    await screen.findByTestId('social-login-checked')
    expect(api.callsTo('GET', '/auth/providers')).toHaveLength(1)
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
    expect(container).not.toHaveTextContent('ou')
  })

  it('se a API falhar, esconde os botões em vez de levar a um erro', async () => {
    mockApi({ 'GET /auth/providers': apiError(503, 'Indisponível.') })
    render(<SocialLoginButtons />)

    await screen.findByTestId('social-login-checked')
    expect(screen.queryByRole('link')).not.toBeInTheDocument()
  })
})
