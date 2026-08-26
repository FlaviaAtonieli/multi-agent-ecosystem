import { FormEvent, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { agentSkillsApi } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'

export function AgentSkillImportPage() {
  const navigate = useNavigate()
  const [manifestMarkdown, setManifestMarkdown] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setSubmitting(true)
    setError('')

    try {
      await agentSkillsApi.importSkill(manifestMarkdown)
      navigate('/agent-skills')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível importar o manifesto.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="workspace-page workspace-page-narrow">
      <section className="workspace-page-heading">
        <div>
          <span className="workspace-eyebrow">IMPORTAR MANIFESTO</span>
          <h1>Registrar Agent Skill a partir do modelo.md</h1>
          <p>
            Cole o conteúdo completo do manifesto. Ele precisa conter as seções obrigatórias: Identificação,
            Objetivo, Capacidades, Entradas Esperadas, Saídas Produzidas, Limites de Atuação, Contrato de
            Entrada, Contrato de Saída, Regras de Segurança, Exemplos de Uso e Critérios de Validação.
          </p>
        </div>
      </section>

      <form className="workspace-form-panel" onSubmit={handleSubmit}>
        <div className="workspace-form-grid">
          <label className="workspace-field workspace-field-full">
            Conteúdo do manifesto (modelo.md)
            <textarea
              value={manifestMarkdown}
              onChange={(event) => setManifestMarkdown(event.target.value)}
              rows={20}
              required
              placeholder="# Nome do Agente&#10;&#10;## Identificação&#10;- Versão: 1.0&#10;- Autor/Origem: ...&#10;- Domínio de atuação: código legado&#10;..."
            />
            <small>O manifesto é validado por completo; qualquer seção ausente é reportada de uma vez.</small>
          </label>
        </div>

        {error && <div className="alert alert-error">{error}</div>}

        <div className="workspace-form-actions">
          <button type="button" className="workspace-secondary-action" onClick={() => navigate(-1)}>
            Cancelar
          </button>
          <button type="submit" className="workspace-primary-action" disabled={submitting}>
            {submitting ? 'Importando…' : 'Importar manifesto'}
          </button>
        </div>
      </form>
    </div>
  )
}
