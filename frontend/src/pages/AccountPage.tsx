import { FormEvent, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi, User } from '../api/authApi'
import { Clan, clansApi } from '../api/clansApi'
import { ApiError } from '../api/http'
import { useAuth } from '../auth/AuthContext'

const roleLabels: Record<User['role'], string> = {
  USER: 'Usuário',
  TECHNICIAN: 'Usuário técnico',
  REVIEWER: 'Revisor',
  ADMIN: 'Administrador',
}

export function AccountPage() {
  const { user, refreshUser, deleteAccount } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState(user?.name ?? '')
  const [nameSaving, setNameSaving] = useState(false)
  const [nameMessage, setNameMessage] = useState('')
  const [nameError, setNameError] = useState('')

  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [passwordSaving, setPasswordSaving] = useState(false)
  const [passwordMessage, setPasswordMessage] = useState('')
  const [passwordError, setPasswordError] = useState('')

  const [myClans, setMyClans] = useState<Clan[]>([])

  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const [deleteConfirmationEmail, setDeleteConfirmationEmail] = useState('')
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  useEffect(() => {
    setName(user?.name ?? '')
  }, [user?.name])

  useEffect(() => {
    clansApi.listMine().then(setMyClans).catch(() => undefined)
  }, [])

  async function handleSaveName(event: FormEvent) {
    event.preventDefault()
    if (!name.trim() || name.trim() === user?.name) return
    setNameSaving(true)
    setNameError('')
    setNameMessage('')
    try {
      await authApi.updateName(name.trim())
      await refreshUser()
      setNameMessage('Nome atualizado.')
    } catch (caught) {
      setNameError(caught instanceof ApiError ? caught.message : 'Não foi possível atualizar o nome.')
    } finally {
      setNameSaving(false)
    }
  }

  async function handleChangePassword(event: FormEvent) {
    event.preventDefault()
    setPasswordError('')
    setPasswordMessage('')
    if (newPassword !== confirmPassword) {
      setPasswordError('A confirmação não bate com a nova senha.')
      return
    }
    setPasswordSaving(true)
    try {
      await authApi.changePassword(currentPassword, newPassword)
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
      setPasswordMessage('Senha alterada.')
    } catch (caught) {
      setPasswordError(caught instanceof ApiError ? caught.message : 'Não foi possível alterar a senha.')
    } finally {
      setPasswordSaving(false)
    }
  }

  async function handleDeleteAccount() {
    if (deleteConfirmationEmail.trim().toLowerCase() !== user?.email.toLowerCase()) {
      setDeleteError('Digite seu e-mail exatamente como cadastrado para confirmar.')
      return
    }
    setDeleting(true)
    setDeleteError('')
    try {
      await deleteAccount()
      navigate('/login', { replace: true })
    } catch (caught) {
      setDeleteError(caught instanceof ApiError ? caught.message : 'Não foi possível excluir a conta.')
      setDeleting(false)
    }
  }

  if (!user) return null

  return (
    <div className="workspace-page workspace-page-narrow">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">MINHA CONTA</span>
          <h1>Conta e preferências</h1>
          <p>Gerencie seus dados de perfil, segurança e participação em clãs.</p>
        </div>
      </section>

      <div className="workspace-account-grid fade-up" style={{ animationDelay: '0.06s' }}>
        <article className="workspace-panel">
          <span className="workspace-card-kicker">PERFIL</span>
          <form className="workspace-form-grid" onSubmit={handleSaveName}>
            <label className="workspace-field workspace-field-full">
              Nome
              <input value={name} onChange={(event) => setName(event.target.value)} maxLength={80} />
            </label>
            <label className="workspace-field workspace-field-full">
              E-mail
              <input value={user.email} disabled />
              <small>{user.has_password ? 'Login por e-mail e senha.' : 'Conta vinculada ao GitHub.'}</small>
            </label>
            {nameError && <div className="alert alert-error">{nameError}</div>}
            {nameMessage && <div className="alert alert-success">{nameMessage}</div>}
            <button
              className="workspace-primary-action"
              type="submit"
              disabled={nameSaving || !name.trim() || name.trim() === user.name}
            >
              {nameSaving ? 'Salvando…' : 'Salvar nome'}
            </button>
          </form>
        </article>

        {user.has_password && (
          <article className="workspace-panel">
            <span className="workspace-card-kicker">SEGURANÇA</span>
            <form className="workspace-form-grid" onSubmit={handleChangePassword}>
              <label className="workspace-field workspace-field-full">
                Senha atual
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  required
                />
              </label>
              <label className="workspace-field workspace-field-full">
                Nova senha
                <input
                  type="password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  minLength={12}
                  required
                />
                <small>Mínimo 12 caracteres, com maiúscula, minúscula, número e caractere especial.</small>
              </label>
              <label className="workspace-field workspace-field-full">
                Confirmar nova senha
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  required
                />
              </label>
              {passwordError && <div className="alert alert-error">{passwordError}</div>}
              {passwordMessage && <div className="alert alert-success">{passwordMessage}</div>}
              <button className="workspace-primary-action" type="submit" disabled={passwordSaving}>
                {passwordSaving ? 'Alterando…' : 'Alterar senha'}
              </button>
            </form>
          </article>
        )}

        <article className="workspace-panel">
          <span className="workspace-card-kicker">PAPEL</span>
          <p className="workspace-account-role">
            <span className={`workspace-status workspace-status-${user.role === 'ADMIN' ? 'completed' : 'received'}`}>
              {roleLabels[user.role]}
            </span>
          </p>
          <small>Só um ADMIN pode alterar seu papel, pela página de Administração.</small>
        </article>

        <article className="workspace-panel">
          <span className="workspace-card-kicker">CLÃS · {myClans.length}</span>
          {myClans.length === 0 ? (
            <div className="workspace-empty">Você ainda não participa de nenhum clã.</div>
          ) : (
            <ul className="workspace-account-clan-list">
              {myClans.map((clan) => (
                <li key={clan.id}>
                  <strong>{clan.name}</strong>
                  <small>
                    {clan.member_count} {clan.member_count === 1 ? 'membro' : 'membros'}
                  </small>
                </li>
              ))}
            </ul>
          )}
          <Link className="workspace-secondary-action workspace-account-clan-link" to="/clans">
            Gerenciar clãs →
          </Link>
        </article>

        <article className="workspace-panel workspace-danger-zone">
          <span className="workspace-card-kicker workspace-danger-kicker">ZONA DE RISCO</span>
          <p>
            Excluir a conta desativa seu acesso e remove seus dados pessoais visíveis (nome, e-mail). O
            histórico de solicitações, skills e clãs que você criou permanece registrado, sem ficar
            atribuído ao seu nome.
          </p>
          {!confirmingDelete ? (
            <button
              type="button"
              className="workspace-action-outline-danger"
              onClick={() => setConfirmingDelete(true)}
            >
              Excluir minha conta
            </button>
          ) : (
            <div className="workspace-delete-confirm">
              <label className="workspace-field workspace-field-full">
                Digite <strong>{user.email}</strong> para confirmar
                <input
                  value={deleteConfirmationEmail}
                  onChange={(event) => setDeleteConfirmationEmail(event.target.value)}
                  placeholder={user.email}
                />
              </label>
              {deleteError && <div className="alert alert-error">{deleteError}</div>}
              <div className="workspace-delete-confirm-actions">
                <button
                  type="button"
                  className="workspace-secondary-action"
                  onClick={() => {
                    setConfirmingDelete(false)
                    setDeleteConfirmationEmail('')
                    setDeleteError('')
                  }}
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  className="workspace-action-outline-danger"
                  disabled={deleting}
                  onClick={handleDeleteAccount}
                >
                  {deleting ? 'Excluindo…' : 'Confirmar exclusão'}
                </button>
              </div>
            </div>
          )}
        </article>
      </div>
    </div>
  )
}
