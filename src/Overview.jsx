export default function Overview() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-black px-6 text-white">
      <div className="text-center">
        <p className="text-sm uppercase tracking-[0.35em] text-white/45">
          Em desenvolvimento
        </p>
        <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em] text-white">
          Página em construção
        </h1>
        <p className="mt-4 text-white/65">
          Esta etapa do projeto ainda está sendo desenvolvida.
        </p>

        <a
          href="/"
          className="mt-8 inline-flex rounded-full border border-white/12 bg-white/6 px-6 py-3 text-sm uppercase tracking-[0.2em] text-white/75 backdrop-blur-md transition hover:bg-white/10 hover:text-white"
        >
          Voltar
        </a>
      </div>
    </div>
  )
}