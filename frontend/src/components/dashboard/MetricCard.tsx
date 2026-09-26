type MetricCardProps = {
  label: string
  value: string | number
  helper: string
  icon: string
  tone?: 'default' | 'accent' | 'warning' | 'info' | 'success'
  highlight?: boolean
}

export function MetricCard({ label, value, helper, icon, tone = 'default', highlight = false }: MetricCardProps) {
  return (
    <article className={`workspace-metric-card workspace-tone-${tone}${highlight ? ' workspace-metric-card-highlight' : ''}`}>
      <span className={`workspace-metric-icon workspace-metric-icon-${tone}`} aria-hidden="true">{icon}</span>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </article>
  )
}
