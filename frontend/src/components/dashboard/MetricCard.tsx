type MetricCardProps = {
  label: string
  value: string | number
  helper: string
  tone?: 'default' | 'accent' | 'warning'
}

export function MetricCard({ label, value, helper, tone = 'default' }: MetricCardProps) {
  return (
    <article className={`workspace-metric-card workspace-tone-${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
      <small>{helper}</small>
    </article>
  )
}
