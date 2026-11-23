import { useEffect, useState } from 'react'
import { authApi, SocialLoginProviders } from '../api/authApi'
import { GitHubLoginButton } from './GitHubLoginButton'
import { GoogleLoginButton } from './GoogleLoginButton'

// Só mostra o botão de um login social que o backend diz estar ligado: um botão de
// login desligado levaria a pessoa a uma página de erro.
export function SocialLoginButtons() {
  const [providers, setProviders] = useState<SocialLoginProviders | null>(null)

  useEffect(() => {
    let active = true
    authApi
      .providers()
      .then((result) => active && setProviders(result))
      .catch(() => active && setProviders({ github: false, google: false }))
    return () => {
      active = false
    }
  }, [])

  if (providers === null) return null
  if (!providers.github && !providers.google) return <span data-testid="social-login-checked" hidden />

  return (
    <>
      <span data-testid="social-login-checked" hidden />
      <div className="auth-divider">ou</div>
      {providers.github && <GitHubLoginButton />}
      {providers.google && <GoogleLoginButton />}
    </>
  )
}
