import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it } from 'vitest'
import { PrivacyPage } from './PrivacyPage'

function renderPage() {
  return render(
    <MemoryRouter>
      <PrivacyPage />
    </MemoryRouter>,
  )
}

describe('PrivacyPage', () => {
  it('informa o que é guardado, com quem é compartilhado e como excluir', () => {
    renderPage()

    expect(screen.getByRole('heading', { name: 'Política de privacidade' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Dados que guardamos' })).toBeInTheDocument()
    expect(screen.getByText(/OpenRouter/)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Seus direitos' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Minha conta' })).toHaveAttribute('href', '/account')
  })

  it('avisa para não enviar dado sensível', () => {
    renderPage()

    expect(screen.getByText(/Não envie dados pessoais de terceiros/)).toBeInTheDocument()
  })
})
