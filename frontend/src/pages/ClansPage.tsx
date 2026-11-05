import { FormEvent, useEffect, useState } from 'react'
import { AgentSkill, agentSkillsApi } from '../api/agentSkillsApi'
import { Clan, ClanDetail, ClanPolicy, ClanSettings, clansApi } from '../api/clansApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

const DEFAULT_SETTINGS: ClanSettings = { is_open: false, skills_policy: 'ALL_MEMBERS', members_policy: 'ALL_MEMBERS' }

const policyLabels: Record<ClanPolicy, string> = {
  ALL_MEMBERS: 'Todos os membros',
  OWNER_ONLY: 'Só o dono',
}

type SettingsFieldsProps = {
  value: ClanSettings
  disabled?: boolean
  onChange: (patch: Partial<ClanSettings>) => void
}

function ClanSettingsFields({ value, disabled, onChange }: SettingsFieldsProps) {
  return (
    <div className="workspace-clan-settings">
      <label>
        <span>Acesso</span>
        <select
          value={value.is_open ? 'open' : 'closed'}
          disabled={disabled}
          onChange={(event) => onChange({ is_open: event.target.value === 'open' })}
        >
          <option value="closed">Fechado — só entra quem for adicionado</option>
          <option value="open">Aberto — qualquer um pode entrar</option>
        </select>
      </label>
      <label>
        <span>Quem adiciona Agent Skills</span>
        <select
          value={value.skills_policy}
          disabled={disabled}
          onChange={(event) => onChange({ skills_policy: event.target.value as ClanPolicy })}
        >
          <option value="ALL_MEMBERS">{policyLabels.ALL_MEMBERS}</option>
          <option value="OWNER_ONLY">{policyLabels.OWNER_ONLY}</option>
        </select>
      </label>
      <label>
        <span>Quem adiciona/remove membros</span>
        <select
          value={value.members_policy}
          disabled={disabled}
          onChange={(event) => onChange({ members_policy: event.target.value as ClanPolicy })}
        >
          <option value="ALL_MEMBERS">{policyLabels.ALL_MEMBERS}</option>
          <option value="OWNER_ONLY">{policyLabels.OWNER_ONLY}</option>
        </select>
      </label>
    </div>
  )
}

export function ClansPage() {
  const { user } = useAuth()
  const [clans, setClans] = useState<Clan[]>([])
  const [selected, setSelected] = useState<ClanDetail | null>(null)
  const [newClanName, setNewClanName] = useState('')
  const [newClanSettings, setNewClanSettings] = useState<ClanSettings>(DEFAULT_SETTINGS)
  const [newMemberEmail, setNewMemberEmail] = useState('')
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [pending, setPending] = useState(false)
  // null = não está renomeando; string = rascunho do novo nome.
  const [renameDraft, setRenameDraft] = useState<string | null>(null)
  const [skills, setSkills] = useState<AgentSkill[]>([])
  // null = sem acesso: clã fechado de que o usuário não é membro.
  const [clanSkills, setClanSkills] = useState<AgentSkill[] | null>(null)
  const [skillToAdd, setSkillToAdd] = useState('')

  function loadSkills() {
    agentSkillsApi.listSkills(false).then(setSkills).catch(() => undefined)
  }

  useEffect(loadSkills, [])

  function load() {
    clansApi
      .list()
      .then(setClans)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar os clãs.'))
  }

  useEffect(load, [])

  const selectedId = selected?.id
  const isMember = Boolean(selected?.members.some((m) => m.user_id === user?.id))

  function loadClanSkills(clanId: string) {
    clansApi
      .listSkills(clanId)
      .then(setClanSkills)
      .catch(() => setClanSkills(null))
  }

  useEffect(() => {
    setClanSkills(null)
    setSkillToAdd('')
    if (selectedId) loadClanSkills(selectedId)
  }, [selectedId, isMember])

  function openClan(clanId: string) {
    setError('')
    setRenameDraft(null)
    clansApi
      .get(clanId)
      .then(setSelected)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível abrir o clã.'))
  }

  async function handleCreate(event: FormEvent) {
    event.preventDefault()
    if (!newClanName.trim()) return
    setCreating(true)
    setError('')
    try {
      const clan = await clansApi.create(newClanName.trim(), newClanSettings)
      setNewClanName('')
      setNewClanSettings(DEFAULT_SETTINGS)
      load()
      setSelected(clan)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível criar o clã.')
    } finally {
      setCreating(false)
    }
  }

  // Envolve as ações sobre o clã selecionado: pending/erro e recarga da lista.
  async function runOnSelected(action: (clan: ClanDetail) => Promise<ClanDetail>, fallbackError: string) {
    if (!selected) return
    setPending(true)
    setError('')
    try {
      const updated = await action(selected)
      setSelected(updated)
      load()
      loadSkills()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : fallbackError)
    } finally {
      setPending(false)
    }
  }

  async function handleAddMember(event: FormEvent) {
    event.preventDefault()
    if (!newMemberEmail.trim()) return
    await runOnSelected(async (clan) => {
      const updated = await clansApi.addMember(clan.id, newMemberEmail.trim())
      setNewMemberEmail('')
      return updated
    }, 'Não foi possível adicionar esse usuário.')
  }

  function handleRemoveMember(userId: string) {
    return runOnSelected((clan) => clansApi.removeMember(clan.id, userId), 'Não foi possível remover esse membro.')
  }

  function handleJoin() {
    return runOnSelected((clan) => clansApi.join(clan.id), 'Não foi possível entrar no clã.')
  }

  async function changeClanSkills(action: (clanId: string) => Promise<unknown>, fallbackError: string) {
    if (!selected) return
    setPending(true)
    setError('')
    try {
      await action(selected.id)
      setSkillToAdd('')
      loadClanSkills(selected.id)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : fallbackError)
    } finally {
      setPending(false)
    }
  }

  function handleAddSkill(event: FormEvent) {
    event.preventDefault()
    if (!skillToAdd) return
    return changeClanSkills((clanId) => clansApi.addSkill(clanId, skillToAdd), 'Não foi possível adicionar a skill.')
  }

  function handleRemoveSkill(skillId: string) {
    return changeClanSkills((clanId) => clansApi.removeSkill(clanId, skillId), 'Não foi possível remover a skill.')
  }

  function handleSettingsChange(patch: Partial<ClanSettings>) {
    return runOnSelected(
      (clan) => clansApi.updateSettings(clan.id, patch),
      'Não foi possível salvar as configurações do clã.',
    )
  }

  async function handleRename(event: FormEvent) {
    event.preventDefault()
    const name = renameDraft?.trim() ?? ''
    if (name.length < 2) return
    await runOnSelected(async (clan) => {
      const updated = await clansApi.updateSettings(clan.id, { name })
      setRenameDraft(null)
      return updated
    }, 'Não foi possível renomear o clã.')
  }

  const isOwner = Boolean(selected && selected.created_by_id === user?.id)
  const canManageMembers = isOwner || (isMember && selected?.members_policy === 'ALL_MEMBERS')
  const canEditSettings = isOwner
  const canChangeSkills = isOwner || (isMember && selected?.skills_policy === 'ALL_MEMBERS')
  const clanSkillIds = new Set(clanSkills?.map((skill) => skill.id))
  const skillsToOffer = skills.filter((skill) => skill.enabled && !clanSkillIds.has(skill.id))

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">CLÃS</span>
          <h1>Clãs do ecossistema</h1>
          <p>
            Qualquer pessoa pode criar um clã e definir as regras dele: se é aberto ou fechado, e quem pode adicionar
            Agent Skills e membros. Toda orquestração usa as Agent Skills de um clã, então adicione aqui as skills
            publicadas no catálogo que fazem sentido para o grupo.
          </p>
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="workspace-detail-grid">
        <article className="workspace-panel">
          <span className="workspace-card-kicker">TODOS OS CLÃS · {clans.length}</span>

          <form className="workspace-clan-create-form" onSubmit={handleCreate}>
            <div className="workspace-clan-create">
              <input
                type="text"
                placeholder="Nome do novo clã..."
                value={newClanName}
                onChange={(event) => setNewClanName(event.target.value)}
                maxLength={120}
              />
              <button className="workspace-primary-action" type="submit" disabled={creating || !newClanName.trim()}>
                {creating ? 'Criando…' : '+ Criar clã'}
              </button>
            </div>
            <ClanSettingsFields
              value={newClanSettings}
              disabled={creating}
              onChange={(patch) => setNewClanSettings((current) => ({ ...current, ...patch }))}
            />
          </form>

          {clans.length === 0 ? (
            <div className="workspace-empty">Nenhum clã criado ainda.</div>
          ) : (
            <ul className="workspace-clan-list">
              {clans.map((clan) => (
                <li key={clan.id}>
                  <button
                    type="button"
                    className={`workspace-clan-list-item${selected?.id === clan.id ? ' active' : ''}`}
                    onClick={() => openClan(clan.id)}
                  >
                    <strong>{clan.name}</strong>
                    <small>
                      {clan.is_open ? 'Aberto' : 'Fechado'} · {clan.member_count}{' '}
                      {clan.member_count === 1 ? 'membro' : 'membros'}
                    </small>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </article>

        <article className="workspace-panel">
          {!selected ? (
            <div className="workspace-empty">Selecione um clã à esquerda para ver os membros.</div>
          ) : (
            <>
              {renameDraft !== null ? (
                <form className="workspace-clan-rename" onSubmit={handleRename}>
                  <input
                    type="text"
                    value={renameDraft}
                    onChange={(event) => setRenameDraft(event.target.value)}
                    maxLength={120}
                    aria-label="Novo nome do clã"
                  />
                  <button
                    className="workspace-primary-action"
                    type="submit"
                    disabled={pending || renameDraft.trim().length < 2 || renameDraft.trim() === selected.name}
                  >
                    Salvar
                  </button>
                  <button
                    className="workspace-secondary-action"
                    type="button"
                    disabled={pending}
                    onClick={() => setRenameDraft(null)}
                  >
                    Cancelar
                  </button>
                </form>
              ) : (
                <div className="workspace-clan-title">
                  <span className="workspace-card-kicker">{selected.name.toUpperCase()}</span>
                  {canEditSettings && (
                    <button
                      type="button"
                      className="workspace-clan-rename-trigger"
                      onClick={() => setRenameDraft(selected.name)}
                    >
                      Renomear
                    </button>
                  )}
                </div>
              )}
              <p className="workspace-clan-created">
                Criado em {new Date(selected.created_at).toLocaleDateString('pt-BR')}
              </p>

              {!isMember && selected.is_open && (
                <button
                  type="button"
                  className="workspace-primary-action workspace-clan-join"
                  disabled={pending}
                  onClick={handleJoin}
                >
                  Entrar no clã
                </button>
              )}

              {canEditSettings ? (
                <ClanSettingsFields value={selected} disabled={pending} onChange={handleSettingsChange} />
              ) : (
                <ul className="workspace-clan-rules">
                  <li>{selected.is_open ? 'Aberto — qualquer um pode entrar' : 'Fechado — só entra quem for adicionado'}</li>
                  <li>Agent Skills: {policyLabels[selected.skills_policy].toLowerCase()}</li>
                  <li>Membros: {policyLabels[selected.members_policy].toLowerCase()}</li>
                </ul>
              )}

              <ul className="workspace-clan-members">
                {selected.members.map((member) => {
                  const isSelf = member.user_id === user?.id
                  const isClanOwner = member.user_id === selected.created_by_id
                  const canRemove = isSelf || (canManageMembers && !isClanOwner)
                  return (
                    <li key={member.user_id}>
                      <div>
                        <strong>
                          {member.name}
                          {isClanOwner && ' · dono'}
                        </strong>
                        <small>{member.email}</small>
                      </div>
                      {canRemove && (
                        <button
                          type="button"
                          className="workspace-secondary-action"
                          disabled={pending}
                          onClick={() => handleRemoveMember(member.user_id)}
                        >
                          {isSelf ? 'Sair' : 'Remover'}
                        </button>
                      )}
                    </li>
                  )
                })}
              </ul>

              {canManageMembers ? (
                <form className="workspace-clan-add-member" onSubmit={handleAddMember}>
                  <input
                    type="email"
                    placeholder="E-mail do usuário a adicionar..."
                    value={newMemberEmail}
                    onChange={(event) => setNewMemberEmail(event.target.value)}
                  />
                  <button className="workspace-secondary-action" type="submit" disabled={pending || !newMemberEmail.trim()}>
                    + Adicionar
                  </button>
                </form>
              ) : (
                <small className="workspace-clan-hint">
                  {selected.members_policy === 'OWNER_ONLY'
                    ? 'Neste clã, só o dono pode adicionar ou remover pessoas.'
                    : 'Só quem já é membro deste clã pode adicionar ou remover outras pessoas.'}
                </small>
              )}

              <span className="workspace-card-kicker workspace-clan-skills-kicker">
                AGENT SKILLS DO CLÃ · {clanSkills ? clanSkills.length : '—'}
              </span>
              {!clanSkills ? (
                <small className="workspace-clan-hint">Só membros do clã enxergam as Agent Skills dele.</small>
              ) : clanSkills.length === 0 ? (
                <small className="workspace-clan-hint">Nenhuma skill neste clã ainda.</small>
              ) : (
                <ul className="workspace-clan-members">
                  {clanSkills.map((skill) => (
                    <li key={skill.id}>
                      <div>
                        <strong>{skill.name}</strong>
                        <small>{skill.objective}</small>
                      </div>
                      {canChangeSkills ? (
                        <button
                          type="button"
                          className="workspace-secondary-action"
                          disabled={pending}
                          aria-label={`Remover ${skill.name} do clã`}
                          onClick={() => handleRemoveSkill(skill.id)}
                        >
                          Remover
                        </button>
                      ) : (
                        <code>{skill.version}</code>
                      )}
                    </li>
                  ))}
                </ul>
              )}

              {canChangeSkills && clanSkills && (
                <form className="workspace-clan-add-member" onSubmit={handleAddSkill}>
                  <select
                    aria-label="Skill para adicionar"
                    value={skillToAdd}
                    onChange={(event) => setSkillToAdd(event.target.value)}
                  >
                    <option value="">Escolha uma skill do catálogo...</option>
                    {skillsToOffer.map((skill) => (
                      <option key={skill.id} value={skill.id}>
                        {skill.name}
                      </option>
                    ))}
                  </select>
                  <button className="workspace-secondary-action" type="submit" disabled={pending || !skillToAdd}>
                    Adicionar skill
                  </button>
                </form>
              )}
            </>
          )}
        </article>
      </div>
    </div>
  )
}
