import { Link } from 'react-router-dom'
import Header from '../components/layout/Header'
import Footer from '../components/layout/Footer'
import NeuralNetwork from '../components/neural/NeuralNetwork'
import AuthCard from '../components/auth/AuthCard'
import AuthInput from '../components/auth/AuthInput'
import SocialAuthButton from '../components/auth/SocialAuthButton'


export default function AuthPage() {
  const handleSubmit = event => {
    event.preventDefault()
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      <NeuralNetwork />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(110,231,255,0.10),transparent_22%),radial-gradient(circle_at_25%_25%,rgba(59,130,246,0.08),transparent_18%),radial-gradient(circle_at_75%_70%,rgba(255,79,163,0.08),transparent_18%),radial-gradient(circle_at_80%_20%,rgba(255,138,61,0.06),transparent_16%),radial-gradient(circle_at_20%_80%,rgba(183,255,60,0.06),transparent_14%)]" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/35 via-black/10 to-black/75" />

      <Header
        rightAction={
          <Link
            to="/"
            className="inline-flex items-center rounded-full border border-white/12 bg-white/6 px-5 py-2.5 text-[11px] font-light uppercase tracking-[0.28em] text-white/78 backdrop-blur-md transition duration-300 hover:border-cyan-300/30 hover:bg-white/10 hover:text-white"
          >
            Voltar ao início
          </Link>
        }
      />

      <main className="relative z-10 flex min-h-[calc(100vh-160px)] items-start px-6 py-10 md:py-12">
        <div className="mx-auto w-full max-w-7xl">
          <div className="mb-8 text-center">
                <h1 className="bg-[linear-gradient(90deg,#ffffff_0%,#6ee7ff_30%,#3b82f6_56%,#ff4fa3_86%,#b7ff3c_100%)] bg-clip-text text-4xl font-semibold tracking-[-0.05em] text-transparent md:text-6xl">
                    Acesso à Plataforma
                </h1>
            </div>

          <div className="grid items-start gap-6 lg:grid-cols-2">
            <AuthCard
            eyebrow="Acesso"
            title="Login"
            description="Entre com suas credenciais para continuar sua navegação no projeto."
            >
            <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                <button
                    type="button"
                    className="flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/4 px-4 py-3 text-sm text-white/75 backdrop-blur-md transition hover:border-white/20 hover:bg-white/8 hover:text-white"
                >
                    <span className="text-base">G</span>
                    <span>Google</span>
                </button>

                <button
                    type="button"
                    className="flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/4 px-4 py-3 text-sm text-white/75 backdrop-blur-md transition hover:border-white/20 hover:bg-white/8 hover:text-white"
                >
                    <span className="text-base">◉</span>
                    <span>GitHub</span>
                </button>
                </div>

                <div className="relative py-2">
                <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-white/10" />
                </div>
                <div className="relative flex justify-center">
                    <span className="bg-[rgba(6,6,12,0.85)] px-4 text-[10px] uppercase tracking-[0.32em] text-white/35">
                    ou continue com e-mail
                    </span>
                </div>
                </div>

                <form className="space-y-4" onSubmit={handleSubmit}>
                <AuthInput
                    id="login-email"
                    label="E-mail"
                    type="email"
                    placeholder="seuemail@exemplo.com"
                />
                <AuthInput
                    id="login-password"
                    label="Senha"
                    type="password"
                    placeholder="Digite sua senha"
                />

                <div className="flex items-center justify-between text-sm text-white/50">
                    <label className="flex items-center gap-2">
                    <input
                        type="checkbox"
                        className="h-4 w-4 rounded border-white/20 bg-white/5 accent-cyan-400"
                    />
                    Permanecer conectado
                    </label>

                    <a href="#" className="transition hover:text-cyan-300">
                    Esqueci minha senha
                    </a>
                </div>

                <button
                    type="submit"
                    className="w-full rounded-2xl border border-cyan-300/20 bg-[linear-gradient(90deg,rgba(110,231,255,0.14),rgba(59,130,246,0.14),rgba(255,79,163,0.12))] px-5 py-3 text-sm font-medium uppercase tracking-[0.22em] text-white transition hover:border-cyan-300/40 hover:shadow-[0_0_30px_rgba(110,231,255,0.15)]"
                >
                    Entrar
                </button>
                </form>
            </div>
            </AuthCard>

<AuthCard
  eyebrow="Novo acesso"
  title="Cadastro"
  description="Crie uma conta para acompanhar a evolução da arquitetura e das próximas etapas."
>
  <div className="space-y-4">
    <div className="grid gap-3 sm:grid-cols-2">
      <button
        type="button"
        className="flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/4 px-4 py-3 text-sm text-white/75 backdrop-blur-md transition hover:border-white/20 hover:bg-white/8 hover:text-white"
      >
        <span className="text-base">G</span>
        <span>Google</span>
      </button>

      <button
        type="button"
        className="flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/4 px-4 py-3 text-sm text-white/75 backdrop-blur-md transition hover:border-white/20 hover:bg-white/8 hover:text-white"
      >
        <span className="text-base">◉</span>
        <span>GitHub</span>
      </button>
    </div>

    <div className="relative py-2">
      <div className="absolute inset-0 flex items-center">
        <div className="w-full border-t border-white/10" />
      </div>
      <div className="relative flex justify-center">
        <span className="bg-[rgba(6,6,12,0.85)] px-4 text-[10px] uppercase tracking-[0.32em] text-white/35">
          ou crie com e-mail
        </span>
      </div>
    </div>

    <form className="space-y-4" onSubmit={handleSubmit}>
            <AuthInput
                id="register-name"
                label="Nome completo"
                type="text"
                placeholder="Seu nome"
            />
            <AuthInput
                id="register-email"
                label="E-mail"
                type="email"
                placeholder="seuemail@exemplo.com"
            />
            <AuthInput
                id="register-password"
                label="Senha"
                type="password"
                placeholder="Crie uma senha"
            />
            <AuthInput
                id="register-password-confirm"
                label="Confirmar senha"
                type="password"
                placeholder="Repita sua senha"
            />

            <button
                type="submit"
                className="w-full rounded-2xl border border-pink-300/20 bg-[linear-gradient(90deg,rgba(255,79,163,0.12),rgba(167,139,250,0.12),rgba(183,255,60,0.10))] px-5 py-3 text-sm font-medium uppercase tracking-[0.22em] text-white transition hover:border-pink-300/40 hover:shadow-[0_0_30px_rgba(255,79,163,0.15)]"
            >
                Criar conta
            </button>
            </form>
        </div>
        </AuthCard>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}