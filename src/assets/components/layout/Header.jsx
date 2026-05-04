export default function Header({ rightAction = null }) {
  return (
    <header className="relative z-20 border-b border-white/10 bg-black/30 backdrop-blur-md">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-5 md:px-10">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 rounded-full bg-white shadow-[0_0_18px_rgba(255,255,255,0.9)]" />
          <div className="h-3 w-3 rounded-full bg-[#6ee7ff] shadow-[0_0_18px_rgba(110,231,255,0.8)]" />
          <div className="h-3 w-3 rounded-full bg-[#3b82f6] shadow-[0_0_18px_rgba(59,130,246,0.8)]" />
          <div className="h-3 w-3 rounded-full bg-[#ff4fa3] shadow-[0_0_18px_rgba(255,79,163,0.8)]" />
          <div className="h-3 w-3 rounded-full bg-[#ff8a3d] shadow-[0_0_18px_rgba(255,138,61,0.8)]" />
          <div className="h-3 w-3 rounded-full bg-[#b7ff3c] shadow-[0_0_18px_rgba(183,255,60,0.8)]" />
        </div>

        <div className="hidden text-[10px] uppercase tracking-[0.4em] text-white/60 md:block">
          TCC · MULTI-AGENT ECOSYSTEM
        </div>

        <div className="flex items-center">{rightAction}</div>
      </div>
    </header>
  )
}