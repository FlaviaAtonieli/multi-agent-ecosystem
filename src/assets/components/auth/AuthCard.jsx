export default function AuthCard({ eyebrow, title, description, children }) {
  return (
    <section className="group relative overflow-hidden rounded-[28px] p-px self-start">
      <div className="absolute inset-0 rounded-[28px] bg-[linear-gradient(135deg,rgba(255,255,255,0.35)_0%,rgba(110,231,255,0.65)_18%,rgba(59,130,246,0.55)_38%,rgba(167,139,250,0.50)_58%,rgba(255,79,163,0.55)_78%,rgba(183,255,60,0.40)_100%)] opacity-80 blur-[1px] transition duration-500 group-hover:opacity-100" />

      <div className="relative rounded-[27px] border border-white/10 bg-[linear-gradient(180deg,rgba(10,10,18,0.94),rgba(6,6,12,0.90))] p-7 backdrop-blur-xl md:p-8">
        <p className="text-[10px] uppercase tracking-[0.35em] text-white/40">
          {eyebrow}
        </p>

        <h2 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white">
          {title}
        </h2>

        <p className="mt-3 max-w-md text-sm leading-6 text-white/60">
          {description}
        </p>

        <div className="mt-8">{children}</div>
      </div>
    </section>
  )
}