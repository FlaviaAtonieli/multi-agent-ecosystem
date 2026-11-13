import { FormEvent, useCallback, useEffect, useState } from 'react'
import { ClanRepository, ClanRepositoryStatus, clansApi } from '../../api/clansApi'
import { ApiError } from '../../api/http'

const POLL_MS = 3000

const statusLabels: Record<ClanRepositoryStatus, string> = {
  PENDING: 'Na fila',
  INDEXING: 'Indexando…',
  READY: 'Pronto',
  FAILED: 'Falhou',
}

function summary(repository: ClanRepository): string {
  if (repository.status !== 'READY') return statusLabels[repository.status]
  const files = `${repository.file_count} ${repository.file_count === 1 ? 'arquivo' : 'arquivos'}`
  const chunks = `${repository.chunk_count} ${repository.chunk_count === 1 ? 'trecho' : 'trechos'}`
  return `${statusLabels.READY} · ${files} · ${chunks}`
}

type Props = {
  clanId: string
  canSee: boolean
  canChange: boolean
}

// Repositórios públicos do GitHub que alimentam a base de conhecimento do comitê. A
// indexação roda no servidor; a tela consulta de novo enquanto houver algum indexando.
export function ClanRepositories({ clanId, canSee, canChange }: Props) {
  const [repositories, setRepositories] = useState<ClanRepository[] | null>(null)
  const [url, setUrl] = useState('')
  const [pending, setPending] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    try {
      setRepositories(await clansApi.listRepositories(clanId))
    } catch {
      setRepositories((current) => current ?? [])
    }
  }, [clanId])

  useEffect(() => {
    setRepositories(null)
    setError('')
    if (canSee) void load()
  }, [canSee, load])

  const indexing = Boolean(repositories?.some((item) => item.status === 'PENDING' || item.status === 'INDEXING'))
  useEffect(() => {
    if (!indexing) return
    const timer = window.setInterval(() => void load(), POLL_MS)
    return () => window.clearInterval(timer)
  }, [indexing, load])

  async function change(action: () => Promise<unknown>, fallback: string) {
    setPending(true)
    setError('')
    try {
      await action()
      await load()
      return true
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : fallback)
      return false
    } finally {
      setPending(false)
    }
  }

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    const added = await change(() => clansApi.addRepository(clanId, url.trim()), 'Não foi possível adicionar o repositório.')
    if (added) setUrl('')
  }

  if (!canSee) {
    return <small className="workspace-clan-hint">Só membros do comitê enxergam os repositórios dele.</small>
  }

  return (
    <div className="workspace-clan-repositories">
      <small className="workspace-clan-hint">
        Os agentes do comitê consultam o código destes repositórios para responder. Só repositórios públicos do
        GitHub; o código é lido como texto, nunca executado.
      </small>

      {repositories === null ? (
        <small className="workspace-clan-hint">Carregando repositórios…</small>
      ) : repositories.length === 0 ? (
        <small className="workspace-clan-hint">Nenhum repositório neste comitê ainda.</small>
      ) : (
        <ul className="workspace-clan-members">
          {repositories.map((repository) => {
            const fullName = `${repository.owner}/${repository.name}`
            const busy = repository.status === 'PENDING' || repository.status === 'INDEXING'
            return (
              <li key={repository.id} aria-label={fullName}>
                <div>
                  <strong>
                    <a href={repository.url} target="_blank" rel="noreferrer noopener">
                      {fullName}
                    </a>
                  </strong>
                  <small className={`workspace-repository-status workspace-repository-${repository.status.toLowerCase()}`}>
                    {summary(repository)}
                  </small>
                  {repository.status === 'FAILED' && repository.error_message && <small>{repository.error_message}</small>}
                </div>
                {canChange && (
                  <div className="workspace-repository-actions">
                    <button
                      type="button"
                      className="workspace-code-block-action"
                      disabled={pending || busy}
                      aria-label={`Indexar ${fullName} de novo`}
                      onClick={() =>
                        void change(
                          () => clansApi.reindexRepository(clanId, repository.id),
                          'Não foi possível indexar de novo.',
                        )
                      }
                    >
                      Indexar de novo
                    </button>
                    <button
                      type="button"
                      className="workspace-code-block-action"
                      disabled={pending || repository.status === 'INDEXING'}
                      aria-label={`Remover ${fullName}`}
                      onClick={() =>
                        void change(
                          () => clansApi.removeRepository(clanId, repository.id),
                          'Não foi possível remover o repositório.',
                        )
                      }
                    >
                      Remover
                    </button>
                  </div>
                )}
              </li>
            )
          })}
        </ul>
      )}

      {canChange && (
        <form className="workspace-clan-add-member" onSubmit={handleAdd}>
          <input
            type="url"
            aria-label="Endereço do repositório no GitHub"
            placeholder="https://github.com/dono/repositorio"
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <button className="workspace-secondary-action" type="submit" disabled={pending || !url.trim()}>
            Adicionar repositório
          </button>
        </form>
      )}

      {error && (
        <p role="alert" className="alert alert-error">
          {error}
        </p>
      )}
    </div>
  )
}
