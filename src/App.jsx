import Header from './assets/components/Header'
import Footer from './assets/components/Footer'
import NeuralNetwork from './assets/components/NeuralNetwork'

function InfoPill({ children, className = '' }) {
  return (
    <div
      className={`rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs uppercase tracking-[0.25em] text-white/65 backdrop-blur-md ${className}`}
    >
      {children}
    </div>
  )
}

export default function App() {
  return (
    <div className="relative min-h-screen overflow-hidden bg-black text-white">
      <NeuralNetwork />

      <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(110,231,255,0.10),transparent_22%),radial-gradient(circle_at_25%_25%,rgba(59,130,246,0.08),transparent_18%),radial-gradient(circle_at_75%_70%,rgba(255,79,163,0.08),transparent_18%),radial-gradient(circle_at_80%_20%,rgba(255,138,61,0.06),transparent_16%),radial-gradient(circle_at_20%_80%,rgba(183,255,60,0.06),transparent_14%)]" />
      <div className="absolute inset-0 bg-gradient-to-b from-black/35 via-transparent to-black/70" />

      <Header />

      <main className="relative z-10 flex min-h-[calc(100vh-160px)] items-center justify-center px-6 py-12">
        <div className="mx-auto flex max-w-6xl flex-col items-center text-center">
          <div className="mb-8 flex flex-wrap items-center justify-center gap-3">
            <InfoPill>AI Architecture</InfoPill>
            <InfoPill>Specialist Agents</InfoPill>
            <InfoPill>Corporate Ecosystem</InfoPill>
          </div>

          <h1 className="max-w-4xl bg-[linear-gradient(90deg,#ffffff_0%,#6ee7ff_28%,#3b82f6_55%,#a78bfa_77%,#ff4fa3_92%,#b7ff3c_100%)] bg-clip-text px-4 text-5xl font-semibold tracking-[-0.05em] text-transparent md:text-7xl lg:text-8xl">
            multi-agent
            <br />
            ecosystem
          </h1>

          <div className="mt-10">
            <a
              href="/overview"
              className="inline-flex items-center rounded-full border border-white/12 bg-white/6 px-8 py-3 text-sm font-light uppercase tracking-[0.28em] text-white/78 backdrop-blur-md transition duration-300 hover:border-cyan-300/30 hover:bg-white/10 hover:text-white hover:shadow-[0_0_30px_rgba(110,231,255,0.18)]"
            >
              Iniciar
            </a>
          </div>
        </div>
      </main>

      <Footer />
    </div>
  )
}