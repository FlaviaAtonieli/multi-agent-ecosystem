import { render, screen } from '@testing-library/react'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { mockApi, testUser } from '../test/api'
import { App } from './App'

function CurrentPath() {
  return <output aria-label="Endereço atual">{useLocation().pathname}</output>
}

describe('rotas', () => {
  it('o endereço antigo dos clãs leva para os comitês', async () => {
    mockApi({
      'GET /auth/me': testUser,
      'GET /clans': [],
      'GET /agent-skills?only_active=false': [],
    })

    render(
      <MemoryRouter initialEntries={['/clans']}>
        <AuthProvider>
          <App />
          <CurrentPath />
        </AuthProvider>
      </MemoryRouter>,
    )

    expect(await screen.findByRole('heading', { level: 1, name: /Comitês/ })).toBeInTheDocument()
    expect(screen.getByLabelText('Endereço atual')).toHaveTextContent('/comites')
  })
})
