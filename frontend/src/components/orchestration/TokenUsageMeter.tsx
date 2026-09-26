export function TokenUsageMeter({ used, limit }: { used: number; limit: number }) {
  const percentage = limit > 0 ? Math.min(100, Math.round((used / limit) * 100)) : 0
  const tone = used >= limit ? 'danger' : percentage >= 70 ? 'warning' : 'accent'

  return (
    <div className={`workspace-token-meter workspace-token-meter-${tone}`}>
      <div className="workspace-token-meter-header">
        <span>Uso de tokens hoje</span>
        <strong>{percentage}%</strong>
      </div>
      <div className="workspace-token-meter-track">
        <div className="workspace-token-meter-fill" style={{ width: `${percentage}%` }} />
      </div>
      <small>{used.toLocaleString('pt-BR')} de {limit.toLocaleString('pt-BR')} tokens</small>
    </div>
  )
}
