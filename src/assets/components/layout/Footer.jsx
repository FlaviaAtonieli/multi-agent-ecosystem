export default function Footer() {
  return (
    <footer className="relative z-20 border-t border-white/10 bg-gradient-to-b from-transparent via-black/18 to-black/28 backdrop-blur-sm">
      <div className="mx-auto flex max-w-7xl flex-col gap-5 px-6 py-6 md:flex-row md:items-end md:justify-between md:px-10">
        <div className="max-w-md">
          <p className="text-[10px] uppercase tracking-[0.32em] text-white/38">
            Projeto
          </p>
          <p className="mt-2 text-[15px] font-light leading-7 tracking-[0.01em] text-white/68">
            Arquitetura de Integração de Agentes Especialistas em Ambientes
            Corporativos Complexos
          </p>
        </div>

        <div className="max-w-md text-left md:text-right">
          <p className="text-[10px] uppercase tracking-[0.32em] text-white/38">
            Informações do TCC
          </p>
          <p className="mt-2 text-[15px] font-light leading-7 tracking-[0.01em] text-white/68">
            Flavia Antonioli de Souza · Engenharia de Software · 2026
          </p>
        </div>
      </div>
    </footer>
  )
}