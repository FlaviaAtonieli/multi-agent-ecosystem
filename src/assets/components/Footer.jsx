export default function Footer() {
  return (
    <footer className="relative z-20 border-t border-white/10 bg-black/35 backdrop-blur-md">
      <div className="mx-auto grid max-w-7xl gap-6 px-6 py-6 md:grid-cols-[180px_1fr_1fr] md:px-10">
        <div className="flex min-h-24 items-center justify-center ">
         <img src="" alt="" />
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-white/45">Projeto</p>
          <p className="mt-2 text-sm text-white/70">
            Arquitetura de Integração de Agentes 
            Especialistas em Ambientes Corporativos 
          </p>
        </div>

        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-white/45">
            Informações do TCC
          </p>
          <p className="mt-2 text-sm text-white/70">
            · Autora: Flavia Antonieli de Souza  
            · Graduação: Engenharia de Software  
            · 2026
          </p>
        </div>
      </div>
    </footer>
  )
}