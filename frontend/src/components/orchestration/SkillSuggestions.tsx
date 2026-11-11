import { useState } from 'react'
import { Link } from 'react-router-dom'
import { agentSkillsApi, SkillSuggestionsResult } from '../../api/agentSkillsApi'
import { clansApi } from '../../api/clansApi'
import { ApiError } from '../../api/http'
import { domainLabels } from './shared'

type Props = {
  clanId: string
  title: string
  problem: string
  objective: string
  context: string
  onAdded: (domain: string) => void
}

// Só compara embeddings: não consome o modelo de chat. Só roda a pedido da pessoa, e
// o motor apenas sugere: a skill só entra no comitê se ela escolher.
export function SkillSuggestions({ clanId, title, problem, objective, context, onAdded }: Props) {
  const [result, setResult] = useState<SkillSuggestionsResult | null>(null)
  const [added, setAdded] = useState<string[]>([])
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  async function check() {
    setChecking(true)
    setError('')
    setAdded([])
    try {
      setResult(
        await agentSkillsApi.suggestSkills({
          clan_id: clanId,
          title: title.trim(),
          problem: problem.trim(),
          objective: objective.trim(),
          context: context.trim() || null,
        }),
      )
    } catch (caught) {
      setResult(null)
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível verificar as skills.')
    } finally {
      setChecking(false)
    }
  }

  async function add(skillId: string, name: string, domain: string) {
    setError('')
    try {
      await clansApi.addSkill(clanId, skillId)
      setAdded((current) => [...current, name])
      setResult((current) =>
        current && { ...current, suggestions: current.suggestions.filter((item) => item.id !== skillId) },
      )
      onAdded(domain)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível adicionar a skill.')
    }
  }

  return (
    <div className="workspace-field workspace-field-full workspace-skill-suggestions">
      <button type="button" className="workspace-secondary-action" disabled={checking} onClick={check}>
        {checking ? 'Verificando…' : 'Verificar skills que podem ajudar'}
      </button>
      {error && <div className="alert alert-error">{error}</div>}
      {added.map((name) => (
        <small key={name}>{name} entrou no comitê.</small>
      ))}
      {result && !result.available && <small>A sugestão de skills está indisponível agora. Você pode seguir normalmente.</small>}
      {result?.available && result.suggestions.length === 0 && added.length === 0 && result.covered_by_clan && (
        <small>As skills deste comitê já parecem cobrir este assunto.</small>
      )}
      {result?.catalog_gap && (
        <small>
          Nenhuma skill do catálogo parece cobrir este assunto. <Link to="/agent-skills/new">Criar uma skill</Link>
        </small>
      )}
      {result && result.suggestions.length > 0 && (
        <>
          {!result.can_add_to_clan && <small>Só o dono deste comitê pode adicionar skills a ele.</small>}
          <ul className="workspace-artifact-list">
            {result.suggestions.map((item) => (
              <li key={item.id} className="workspace-artifact-row">
                <div className="workspace-artifact-info">
                  <strong>{item.name}</strong>
                  <small>
                    {domainLabels[item.domain] ?? item.domain} · similaridade {Math.round(item.score * 100)}%
                  </small>
                  <small>{item.objective}</small>
                </div>
                {result.can_add_to_clan && (
                  <button
                    type="button"
                    className="workspace-secondary-action"
                    aria-label={`Adicionar ${item.name} ao comitê`}
                    onClick={() => add(item.id, item.name, item.domain)}
                  >
                    Adicionar
                  </button>
                )}
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}
