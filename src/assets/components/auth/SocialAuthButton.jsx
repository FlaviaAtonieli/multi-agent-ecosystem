export default function SocialAuthButton({ provider, icon, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/4 px-4 py-3 text-sm text-white/75 backdrop-blur-md transition hover:border-white/20 hover:bg-white/8 hover:text-white"
    >
      <span className="text-base">{icon}</span>
      <span>{provider}</span>
    </button>
  )
}