import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { AgentSkill, AgentSkillDomain, agentSkillsApi } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

const domainLabels: Record<AgentSkillDomain, string> = {
  codigo_legado: 'Código Legado',
  regras_negocio: 'Regras de Negócio',
  arquitetura_software: 'Arquitetura de Software',
}

export function AgentSkillsPage() {
  const { user } = useAuth()
  const [skills, setSkills] = useState<AgentSkill[]>([])
  const [error, setError] = useState('')
  const [pendingId, setPendingId] = useState<string | null>(null)

  const canImport = user?.role === 'TECHNICIAN' || user?.role === 'ADMIN'
  const canManage = user?.role === 'ADMIN'

  useEffect(() => {
    agentSkillsApi
      .listSkills(false)
      .then(setSkills)
      .catch((caught) =>
        setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar o catálogo.'),
      )
  }, [])

  async function toggleSkill(skill: AgentSkill) {
    setPendingId(skill.id)
    setError('')
    try {
      const updated = skill.enabled
        ? await agentSkillsApi.disableSkill(skill.id)
        : await agentSkillsApi.enableSkill(skill.id)
      setSkills((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível atualizar a Agent Skill.')
    } finally {
      setPendingId(null)
    }
  }

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading">
        <div>
          <span className="workspace-eyebrow">AGENT SKILLS</span>
          <h1>Catálogo de capacidades especializadas</h1>
          <p>Skills registradas, seus domínios de atuação e o estado de habilitação no ecossistema.</p>
        </div>
        {canImport && (
          <Link className="workspace-primary-action" to="/agent-skills/import">
            + Importar manifesto
          </Link>
        )}
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <article className="workspace-panel">
        {skills.length === 0 ? (
          <div className="workspace-empty">Nenhuma Agent Skill registrada ainda.</div>
        ) : (
          <div className="workspace-table-wrap">
            <table className="workspace-table">
              <thead>
                <tr>
                  <th>Skill</th>
                  <th>Domínio</th>
                  <th>Versão</th>
                  <th>Autor/Origem</th>
                  <th>Estado</th>
                  {canManage && <th>Ações</th>}
                </tr>
              </thead>
              <tbody>
                {skills.map((skill) => (
                  <tr key={skill.id}>
                    <td>
                      {skill.name}
                      <small>{skill.objective}</small>
                    </td>
                    <td>{domainLabels[skill.domain]}</td>
                    <td>{skill.version}</td>
                    <td>{skill.author_origin}</td>
                    <td>
                      <span
                        className={`workspace-status workspace-status-${skill.enabled ? 'completed' : 'failed'}`}
                      >
                        {skill.enabled ? 'Habilitada' : 'Desabilitada'}
                      </span>
                    </td>
                    {canManage && (
                      <td>
                        <button
                          type="button"
                          className="workspace-secondary-action"
                          disabled={pendingId === skill.id}
                          onClick={() => toggleSkill(skill)}
                        >
                          {skill.enabled ? 'Desabilitar' : 'Habilitar'}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </article>
    </div>
  )
}
