import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AgentSkillDomain, agentSkillsApi } from '../api/agentSkillsApi'
import { ApiError } from '../api/http'
import { TagListField } from '../components/shared/TagListField'
import { useAuth } from '../auth/AuthContext'

const DOMAIN_OPTIONS: Array<{ value: AgentSkillDomain; label: string }> = [
  { value: 'codigo_legado', label: 'Código Legado' },
  { value: 'regras_negocio', label: 'Regras de Negócio' },
  { value: 'arquitetura_software', label: 'Arquitetura de Software' },
  { value: 'seguranca_informacao', label: 'Segurança da Informação' },
]

// Todo skill hoje usa os mesmos contratos padrão (só existe um schema de
// solicitação/resposta no ecossistema) -- pré-preenchido em vez de pedir pro
// usuário digitar uma referência técnica que não muda entre skills.
const DEFAULT_INPUT_CONTRACT = 'solicitacao_analise_schema.v1'
const DEFAULT_OUTPUT_CONTRACT = 'resposta_especialista_schema.v1'

const STEP_LABELS = ['Identidade', 'Persona', 'Comportamento esperado']

export function AgentSkillCreatePage() {
  const navigate = useNavigate()
  const { user } = useAuth()

  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [domain, setDomain] = useState<AgentSkillDomain>('codigo_legado')
  const [objective, setObjective] = useState('')
  const [personaInstructions, setPersonaInstructions] = useState('')
  const [capabilities, setCapabilities] = useState<string[]>([])
  const [expectedInputs, setExpectedInputs] = useState<string[]>([])
  const [producedOutputs, setProducedOutputs] = useState<string[]>([])
  const [operatingLimits, setOperatingLimits] = useState<string[]>([])
  const [validationCriteria, setValidationCriteria] = useState<string[]>([])
  const [securityRules, setSecurityRules] = useState<string[]>([])
  const [usageExamples, setUsageExamples] = useState<string[]>([])

  const [stepError, setStepError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const nameValid = name.trim().length >= 3
  const objectiveValid = objective.trim().length >= 10

  function goNext() {
    if (step === 1 && !nameValid) {
      setStepError('Dê um nome com pelo menos 3 caracteres para a skill.')
      return
    }
    if (step === 1 && !objectiveValid) {
      setStepError('Descreva o objetivo com um pouco mais de detalhe (mínimo 10 caracteres).')
      return
    }
    if (step === 2 && capabilities.length === 0) {
      setStepError('Adicione ao menos uma capacidade — o que essa skill sabe fazer.')
      return
    }
    setStepError('')
    setStep((current) => Math.min(3, current + 1))
  }

  function goBack() {
    setStepError('')
    setStep((current) => Math.max(1, current - 1))
  }

  async function handleFinalSubmit() {
    if (expectedInputs.length === 0 || producedOutputs.length === 0 || operatingLimits.length === 0 || validationCriteria.length === 0) {
      setStepError('Preencha entradas esperadas, saídas produzidas, limites de atuação e critérios de validação antes de criar a skill.')
      return
    }
    setSubmitting(true)
    setSubmitError('')
    try {
      const created = await agentSkillsApi.createSkill({
        name: name.trim(),
        version: '1.0',
        author_origin: user?.name ?? 'Usuário AgentHub',
        domain,
        objective: objective.trim(),
        capabilities,
        expected_inputs: expectedInputs,
        produced_outputs: producedOutputs,
        operating_limits: operatingLimits,
        input_contract_ref: DEFAULT_INPUT_CONTRACT,
        output_contract_ref: DEFAULT_OUTPUT_CONTRACT,
        security_rules: securityRules,
        usage_examples: usageExamples,
        validation_criteria: validationCriteria,
        uses_external_services: false,
        persona_instructions: personaInstructions.trim() || null,
      })
      navigate(`/agent-skills?created=${created.id}`)
    } catch (caught) {
      setSubmitError(caught instanceof ApiError ? caught.message : 'Não foi possível criar a skill.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="workspace-page workspace-page-narrow">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">NOVA AGENT SKILL</span>
          <h1>Criar uma skill sua</h1>
          <p>
            Ela nasce <strong>privada</strong> — só você vai vê-la e usá-la até decidir compartilhar com um clã ou
            com a rede.
          </p>
        </div>
      </section>

      <ol className="workspace-stepper fade-up" style={{ animationDelay: '0.06s' }}>
        {[1, 2, 3].map((index) => {
          const state = index < step ? 'done' : index === step ? 'current' : 'future'
          return (
            <li key={index} className={`workspace-step workspace-step-${state}`}>
              <span className={`workspace-step-circle${state === 'current' ? ' pop-in' : ''}`}>
                {state === 'done' ? '✓' : index}
              </span>
              <span className="workspace-step-label">{STEP_LABELS[index - 1]}</span>
              {index < 3 && <span className="workspace-step-line" />}
            </li>
          )
        })}
      </ol>

      <div className="workspace-wizard-grid fade-up" style={{ animationDelay: '0.12s' }}>
        <div className="workspace-form-panel workspace-wizard-card">
          {step === 1 && (
            <div className="workspace-form-grid">
              <label className="workspace-field workspace-field-full">
                Nome da skill
                <input
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Ex.: Revisor Cauteloso de Código Legado"
                  autoFocus
                />
                <small>É assim que ela vai aparecer nos cards de resultado e na rede de agentes.</small>
              </label>

              <label className="workspace-field workspace-field-full">
                Domínio de atuação
                <select value={domain} onChange={(event) => setDomain(event.target.value as AgentSkillDomain)}>
                  {DOMAIN_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
                <small>Pode coexistir com outras skills do mesmo domínio — cada uma com sua própria persona.</small>
              </label>

              <label className="workspace-field workspace-field-full">
                Objetivo
                <textarea
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  rows={3}
                  placeholder="O que essa skill se propõe a analisar ou responder?"
                />
              </label>
            </div>
          )}

          {step === 2 && (
            <div className="workspace-form-grid">
              <label className="workspace-field workspace-field-full">
                Persona e instruções
                <textarea
                  value={personaInstructions}
                  onChange={(event) => setPersonaInstructions(event.target.value)}
                  rows={6}
                  placeholder="Como essa skill deve pensar? Ex.: 'Seja extremamente cauteloso: para cada mudança sugerida, aponte o que pode quebrar silenciosamente antes de concluir.'"
                />
                <small>
                  É o que diferencia essa skill de qualquer outra no mesmo domínio — a voz e o foco dela. Opcional,
                  mas é onde a skill ganha personalidade.
                </small>
              </label>

              <TagListField
                label="Capacidades"
                required
                values={capabilities}
                onChange={setCapabilities}
                placeholder="Ex.: Identificar dependências ocultas"
                hint="O que essa skill sabe fazer. Pressione Enter para adicionar cada item."
              />
            </div>
          )}

          {step === 3 && (
            <div className="workspace-form-grid">
              <TagListField
                label="Entradas esperadas"
                required
                values={expectedInputs}
                onChange={setExpectedInputs}
                placeholder="Ex.: Contexto técnico da solicitação"
              />
              <TagListField
                label="Saídas produzidas"
                required
                values={producedOutputs}
                onChange={setProducedOutputs}
                placeholder="Ex.: Lista de riscos priorizados"
              />
              <TagListField
                label="Limites de atuação"
                required
                values={operatingLimits}
                onChange={setOperatingLimits}
                placeholder="Ex.: Não executa nem altera código"
                hint="O que essa skill explicitamente NÃO faz."
              />
              <TagListField
                label="Critérios de validação"
                required
                values={validationCriteria}
                onChange={setValidationCriteria}
                placeholder="Ex.: Cada risco citado precisa de justificativa"
              />
              <TagListField
                label="Regras de segurança (opcional)"
                values={securityRules}
                onChange={setSecurityRules}
                placeholder="Ex.: Nunca expor dados sensíveis do cliente"
              />
              <TagListField
                label="Exemplos de uso (opcional)"
                values={usageExamples}
                onChange={setUsageExamples}
                placeholder="Ex.: Revisar uma proposta de refatoração antes do merge"
              />
            </div>
          )}

          {(stepError || submitError) && <div className="alert alert-error">{stepError || submitError}</div>}

          <div className="workspace-wizard-footer">
            {step === 1 ? (
              <button type="button" className="workspace-secondary-action" onClick={() => navigate(-1)}>
                Cancelar
              </button>
            ) : (
              <button type="button" className="workspace-secondary-action" onClick={goBack}>
                ← Voltar
              </button>
            )}

            {step < 3 ? (
              <button type="button" className="workspace-primary-action" onClick={goNext}>
                Continuar →
              </button>
            ) : (
              <button
                type="button"
                className="workspace-primary-action"
                onClick={handleFinalSubmit}
                disabled={submitting}
              >
                {submitting ? 'Criando…' : 'Criar skill'}
              </button>
            )}
          </div>
        </div>

        <div className="workspace-wizard-side">
          <article className="workspace-panel workspace-panel-secondary">
            <span className="workspace-card-kicker">PRÉVIA</span>
            <div className="workspace-skill-preview-card">
              <span className="workspace-skill-icon workspace-skill-icon-violet">
                {name.trim() ? name.trim().slice(0, 2).toUpperCase() : '··'}
              </span>
              <div>
                <strong>{name.trim() || 'Nome da sua skill'}</strong>
                <small>{DOMAIN_OPTIONS.find((option) => option.value === domain)?.label}</small>
              </div>
            </div>
            <p>{objective.trim() || 'O objetivo aparece aqui conforme você digita.'}</p>
          </article>

          <article className="workspace-tip-box">
            <span className="workspace-tip-icon" aria-hidden="true">i</span>
            <p>
              {step === 1 && 'Escolha um domínio existente mesmo que sua skill tenha uma abordagem diferente das oficiais — a persona é o que a torna única, não o domínio.'}
              {step === 2 && 'Persona forte + poucas capacidades bem definidas gera resultados mais consistentes do que muitas capacidades vagas.'}
              {step === 3 && 'Esses campos guiam o Quality Gate a avaliar a resposta dessa skill com mais rigor — vale investir alguns minutos aqui.'}
            </p>
          </article>
        </div>
      </div>
    </div>
  )
}
