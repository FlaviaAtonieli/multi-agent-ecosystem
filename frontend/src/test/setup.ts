import '@testing-library/jest-dom/vitest'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'

// O jsdom não implementa canvas nem scrollTo. Sem contexto, o AgentNetworkHero
// simplesmente não desenha a animação de fundo.
HTMLCanvasElement.prototype.getContext = (() => null) as unknown as HTMLCanvasElement['getContext']
window.scrollTo = (() => undefined) as typeof window.scrollTo
Element.prototype.scrollIntoView = () => undefined

beforeEach(() => {
  document.cookie = 'agenthub_csrf=token-de-teste; path=/'
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  vi.unstubAllGlobals()
})
