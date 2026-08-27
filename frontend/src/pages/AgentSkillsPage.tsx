import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { AgentSkill, AgentSkillDomain, agentSkillsApi } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

const domainLabels: Record<AgentSkillDomain, string> = {
  codigo_legado: 'Código Legado',
  regras_negocio: 'Regras de Negócio',
  arquitetura_software: 'Arquitetura de Software',
  seguranca_informacao: 'Segurança da Informação',
}

const domainAbbreviations: Record<AgentSkillDomain, string> = {
  codigo_legado: 'CL',
  regras_negocio: 'RN',
  arquitetura_software: 'AS',
  seguranca_informacao: 'SI',
}

const domainTones: Record<AgentSkillDomain, string> = {
  codigo_legado: 'violet',
  regras_negocio: 'green',
  arquitetura_software: 'sky',
  seguranca_informacao: 'red',
}

type StatusFilter = 'ALL' | 'ENABLED' | 'PENDING' | 'DISABLED'

function statusOf(skill: AgentSkill): Exclude<StatusFilter, 'ALL'> {
  if (!skill.enabled) return 'DISABLED'
  return skill.status === 'approved' ? 'ENABLED' : 'PENDING'
}

const statusFilterLabels: Record<StatusFilter, string> = {
  ALL: 'Todas',
  ENABLED: 'Habilitadas',
  PENDING: 'Pendentes',
  DISABLED: 'Desabilitadas',
}

export function AgentSkillsPage() {
  const { user } = useAuth()
  const [skills, setSkills] = useState<AgentSkill[]>([])
  const [error, setError] = useState('')
  const [pendingId, setPendingId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

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

  const counts = useMemo(() => {
    const result: Record<StatusFilter, number> = { ALL: skills.length, ENABLED: 0, PENDING: 0, DISABLED: 0 }
    for (const skill of skills) result[statusOf(skill)] += 1
    return result
  }, [skills])

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase()
    return skills.filter((skill) => {
      const matchesStatus = statusFilter === 'ALL' || statusOf(skill) === statusFilter
      const matchesQuery = !query || skill.name.toLowerCase().includes(query)
      return matchesStatus && matchesQuery
    })
  }, [skills, search, statusFilter])

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
      <section className="workspace-page-heading fade-up">
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

      <div className="workspace-orchestrations-toolbar fade-up" style={{ animationDelay: '0.08s' }}>
        <input
          type="search"
          placeholder="Buscar por nome da skill..."
          value={search}
          onChange={(event) => setSearch(event.target.value)}
        />

        <div className="workspace-filter-chips" role="group" aria-label="Filtrar por estado">
          {(Object.keys(statusFilterLabels) as StatusFilter[]).map((key) => (
            <button
              key={key}
              type="button"
              className={`workspace-filter-chip${statusFilter === key ? ' active' : ''}${key !== 'ALL' ? ` workspace-filter-chip-${key.toLowerCase()}` : ''}`}
              onClick={() => setStatusFilter(key)}
            >
              {statusFilterLabels[key]} · {counts[key]}
            </button>
          ))}
        </div>
      </div>

      {filtered.length === 0 ? (
        <div className="workspace-panel">
          <div className="workspace-empty">
            {skills.length === 0 ? 'Nenhuma Agent Skill registrada ainda.' : 'Nenhuma skill corresponde ao filtro atual.'}
          </div>
        </div>
      ) : (
        <div className="workspace-skill-grid fade-up" style={{ animationDelay: '0.14s' }}>
          {filtered.map((skill) => {
            const status = statusOf(skill)
            return (
              <article key={skill.id} className="workspace-skill-card">
                <div className="workspace-skill-card-top">
                  <span className={`workspace-skill-icon workspace-skill-icon-${domainTones[skill.domain]}`}>
                    {domainAbbreviations[skill.domain]}
                  </span>
                  <span
                    className={`workspace-status ${
                      status === 'ENABLED'
                        ? 'workspace-status-completed'
                        : status === 'PENDING'
                          ? 'workspace-status-awaiting_context'
                          : 'workspace-status-failed'
                    }`}
                  >
                    {status === 'ENABLED' ? 'Habilitada' : status === 'PENDING' ? 'Pendente de validação' : 'Desabilitada'}
                  </span>
                </div>

                <h3 className="workspace-skill-name">{skill.name}</h3>
                <p className="workspace-skill-objective">{skill.objective}</p>

                <div className="workspace-skill-card-footer">
                  <span className="workspace-skill-domain-badge">{domainLabels[skill.domain]}</span>
                  <code>{skill.version}</code>
                </div>

                {canManage && (
                  <button
                    type="button"
                    className="workspace-secondary-action workspace-skill-toggle"
                    disabled={pendingId === skill.id}
                    onClick={() => toggleSkill(skill)}
                  >
                    {skill.enabled ? 'Desabilitar' : 'Habilitar'}
                  </button>
                )}
              </article>
            )
          })}
        </div>
      )}
    </div>
  )
}
