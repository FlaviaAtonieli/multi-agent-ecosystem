export default function AuthInput({ id, label, type, placeholder }) {
  return (
    <div>
      <label
        htmlFor={id}
        className="mb-2 block text-[11px] uppercase tracking-[0.28em] text-white/45"
      >
        {label}
      </label>

      <input
        id={id}
        type={type}
        placeholder={placeholder}
        className="w-full rounded-2xl border border-white/10 bg-white/4 px-4 py-3 text-sm text-white outline-none backdrop-blur-md transition placeholder:text-white/25 focus:border-cyan-300/35 focus:bg-white/6 focus:shadow-[0_0_0_1px_rgba(110,231,255,0.12)]"
      />
    </div>
  )
}