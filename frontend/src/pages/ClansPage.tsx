import { FormEvent, useEffect, useState } from 'react'
import { Clan, ClanDetail, clansApi } from '../api/clansApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

export function ClansPage() {
  const { user } = useAuth()
  const [clans, setClans] = useState<Clan[]>([])
  const [selected, setSelected] = useState<ClanDetail | null>(null)
  const [newClanName, setNewClanName] = useState('')
  const [newMemberEmail, setNewMemberEmail] = useState('')
  const [error, setError] = useState('')
  const [creating, setCreating] = useState(false)
  const [pending, setPending] = useState(false)

  function load() {
    clansApi
      .list()
      .then(setClans)
      .catch((caught) => setError(caught instanceof ApiError ? caught.message : 'Não foi possível carregar os clãs.'))
  }

  useEffect(load, [])

  function openClan(clanId: string) {
    setError('')
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
      const clan = await clansApi.create(newClanName.trim())
      setNewClanName('')
      load()
      setSelected(clan)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível criar o clã.')
    } finally {
      setCreating(false)
    }
  }

  async function handleAddMember(event: FormEvent) {
    event.preventDefault()
    if (!selected || !newMemberEmail.trim()) return
    setPending(true)
    setError('')
    try {
      const updated = await clansApi.addMember(selected.id, newMemberEmail.trim())
      setSelected(updated)
      setNewMemberEmail('')
      load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível adicionar esse usuário.')
    } finally {
      setPending(false)
    }
  }

  async function handleRemoveMember(userId: string) {
    if (!selected) return
    setPending(true)
    setError('')
    try {
      const updated = await clansApi.removeMember(selected.id, userId)
      setSelected(updated)
      load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível remover esse membro.')
    } finally {
      setPending(false)
    }
  }

  const isMember = Boolean(selected?.members.some((m) => m.user_id === user?.id))
  const canManage = isMember || user?.role === 'ADMIN'

  return (
    <div className="workspace-page">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">CLÃS</span>
          <h1>Clãs do ecossistema</h1>
          <p>
            Qualquer pessoa pode criar um clã. Membros de um clã podem adicionar ou remover outros usuários e
            registrar Agent Skills visíveis só para o clã.
          </p>
        </div>
      </section>

      {error && <div className="alert alert-error">{error}</div>}

      <div className="workspace-detail-grid">
        <article className="workspace-panel">
          <span className="workspace-card-kicker">TODOS OS CLÃS · {clans.length}</span>

          <form className="workspace-clan-create" onSubmit={handleCreate}>
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
                      {clan.member_count} {clan.member_count === 1 ? 'membro' : 'membros'}
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
              <span className="workspace-card-kicker">{selected.name.toUpperCase()}</span>
              <p className="workspace-clan-created">
                Criado em {new Date(selected.created_at).toLocaleDateString('pt-BR')}
              </p>

              <ul className="workspace-clan-members">
                {selected.members.map((member) => (
                  <li key={member.user_id}>
                    <div>
                      <strong>{member.name}</strong>
                      <small>{member.email}</small>
                    </div>
                    {canManage && (
                      <button
                        type="button"
                        className="workspace-secondary-action"
                        disabled={pending}
                        onClick={() => handleRemoveMember(member.user_id)}
                      >
                        {member.user_id === user?.id ? 'Sair' : 'Remover'}
                      </button>
                    )}
                  </li>
                ))}
              </ul>

              {canManage ? (
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
                  Só quem já é membro deste clã (ou um ADMIN) pode adicionar ou remover outras pessoas.
                </small>
              )}
            </>
          )}
        </article>
      </div>
    </div>
  )
}
