import { useEffect, useState } from 'react'
import { ApiError } from '../../api/http'
import {
  artifactDownloadUrl,
  artifactsZipUrl,
  orchestrationApi,
  SkillArtifact,
} from '../../api/orchestrationApi'

type Props = {
  traceId: string
  // Muda quando uma resposta nova pode ter trazido mais arquivos.
  refreshKey: number
}

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  return `${Math.round(bytes / 1024)} KB`
}

// Nada aqui chama o modelo: os arquivos já estão guardados no backend. O conteúdo é
// mostrado como texto, então um HTML gerado pelo modelo não roda no site.
export function ArtifactsPanel({ traceId, refreshKey }: Props) {
  const [artifacts, setArtifacts] = useState<SkillArtifact[]>([])
  const [openId, setOpenId] = useState<string | null>(null)
  const [contents, setContents] = useState<Record<string, string>>({})
  const [error, setError] = useState('')

  useEffect(() => {
    orchestrationApi
      .listArtifacts(traceId)
      .then(setArtifacts)
      .catch(() => setArtifacts([]))
  }, [traceId, refreshKey])

  async function toggle(artifactId: string) {
    setError('')
    if (openId === artifactId) {
      setOpenId(null)
      return
    }
    if (contents[artifactId] === undefined) {
      try {
        const artifact = await orchestrationApi.getArtifact(traceId, artifactId)
        setContents((current) => ({ ...current, [artifactId]: artifact.content }))
      } catch (caught) {
        setError(caught instanceof ApiError ? caught.message : 'Não foi possível abrir o arquivo.')
        return
      }
    }
    setOpenId(artifactId)
  }

  if (artifacts.length === 0) return null

  // Cada agente entrega os próprios arquivos (código, documento de design, plano de
  // testes...). Agrupar deixa claro de onde veio cada um.
  const byAgent = new Map<string, SkillArtifact[]>()
  for (const artifact of artifacts) {
    byAgent.set(artifact.agent_skill_name, [...(byAgent.get(artifact.agent_skill_name) ?? []), artifact])
  }

  return (
    <section className="workspace-result-section workspace-artifacts" aria-labelledby="result-material-title">
      <div className="workspace-artifacts-heading">
        <h3 id="result-material-title">
          Material desenvolvido ({artifacts.length} {artifacts.length === 1 ? 'arquivo' : 'arquivos'})
        </h3>
        <a className="workspace-secondary-action" href={artifactsZipUrl(traceId)} download>
          Baixar tudo (.zip)
        </a>
      </div>
      {error && <div className="alert alert-error">{error}</div>}
      {[...byAgent.entries()].map(([agentName, agentArtifacts]) => (
        <div key={agentName} role="group" aria-label={agentName} className="workspace-artifact-group">
          <h4>{agentName}</h4>
          <ul className="workspace-artifact-list">
            {agentArtifacts.map((artifact) => (
              <li key={artifact.id}>
                <div className="workspace-artifact-row">
                  <div className="workspace-artifact-info">
                    <code>{artifact.filename}</code>
                    <small>
                      {formatSize(artifact.size_bytes)} · {artifact.agent_skill_name}
                    </small>
                  </div>
                  <div className="workspace-artifact-actions">
                    <button
                      type="button"
                      className="workspace-code-block-action"
                      aria-expanded={openId === artifact.id}
                      aria-label={`${openId === artifact.id ? 'Ocultar' : 'Visualizar'} ${artifact.filename}`}
                      onClick={() => toggle(artifact.id)}
                    >
                      {openId === artifact.id ? 'Ocultar' : 'Visualizar'}
                    </button>
                    <a
                      className="workspace-code-block-action"
                      href={artifactDownloadUrl(traceId, artifact.id)}
                      download
                      aria-label={`Baixar ${artifact.filename}`}
                    >
                      Baixar
                    </a>
                  </div>
                </div>
                {openId === artifact.id && (
                  <pre className="workspace-code-block">
                    <code>{contents[artifact.id]}</code>
                  </pre>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </section>
  )
}
