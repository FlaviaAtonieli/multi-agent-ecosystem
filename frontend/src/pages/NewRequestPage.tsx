import { ChangeEvent, KeyboardEvent, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ApiError } from '../api/http'
import { orchestrationApi } from '../api/orchestrationApi'

const MAX_ATTACHMENT_BYTES = 300_000
const ALLOWED_ATTACHMENT_EXTENSIONS =
  '.txt,.md,.markdown,.py,.js,.jsx,.ts,.tsx,.java,.go,.rb,.php,.cs,.c,.cpp,.h,.hpp,.kt,.swift,.rs,.json,.yaml,.yml,.xml,.sql,.sh'

type ChecklistState = 'pending' | 'current' | 'done'

type ChecklistItem = {
  key: string
  label: string
  state: ChecklistState
}

const contextSuggestions = ['Módulos', 'Tecnologias', 'Dependências', 'Comportamento esperado']

const stepTips: Record<number, string> = {
  1: 'Um título específico (ex.: "Erro de timeout no serviço de pagamentos") ajuda o Orientador a rotear a demanda mais rápido — e reduz idas e voltas por falta de contexto.',
  2: 'Descreva o comportamento ATUAL antes do esperado, e diferencie sintoma de causa provável — isso evita uma rodada extra de perguntas.',
  3: 'Cite arquivos, módulos ou serviços pelo nome. Solicitações sem isso costumam voltar como "aguardando contexto".',
}

export function NewRequestPage() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)
  const [title, setTitle] = useState('')
  const [problem, setProblem] = useState('')
  const [objective, setObjective] = useState('')
  const [context, setContext] = useState('')
  const [restrictions, setRestrictions] = useState<string[]>(['Não executar alterações automaticamente'])
  const [restrictionDraft, setRestrictionDraft] = useState('')
  const [attachments, setAttachments] = useState<File[]>([])
  const [stepError, setStepError] = useState('')
  const [submitError, setSubmitError] = useState('')
  const [attachmentWarning, setAttachmentWarning] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const titleValid = title.trim().length >= 5 && title.trim().length <= 160
  const problemValid = problem.trim().length >= 10
  const objectiveValid = objective.trim().length >= 5

  const checklist: ChecklistItem[] = useMemo(
    () => [
      { key: 'title', label: 'Título', state: titleValid ? 'done' : step === 1 ? 'current' : 'pending' },
      { key: 'problem', label: 'Problema descrito', state: problemValid ? 'done' : step === 2 ? 'current' : 'pending' },
      { key: 'objective', label: 'Objetivo claro', state: objectiveValid ? 'done' : step === 2 ? 'current' : 'pending' },
      { key: 'context', label: 'Contexto técnico completo', state: step < 3 ? 'pending' : context.trim() ? 'done' : 'current' },
      { key: 'restrictions', label: 'Restrições informadas', state: step < 3 ? 'pending' : restrictions.length > 0 ? 'done' : 'current' },
    ],
    [titleValid, problemValid, objectiveValid, context, restrictions, step],
  )

  function goNext() {
    if (step === 1 && !titleValid) {
      setStepError('Informe um título com pelo menos 5 caracteres.')
      return
    }
    if (step === 2 && (!problemValid || !objectiveValid)) {
      setStepError('Descreva o problema (mín. 10 caracteres) e o objetivo (mín. 5 caracteres).')
      return
    }
    setStepError('')
    setStep((current) => Math.min(3, current + 1))
  }

  function goBack() {
    setStepError('')
    setStep((current) => Math.max(1, current - 1))
  }

  function addRestriction(raw: string) {
    const value = raw.trim()
    if (!value) return
    setRestrictions((current) => (current.includes(value) ? current : [...current, value]))
    setRestrictionDraft('')
  }

  function handleRestrictionKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      addRestriction(restrictionDraft)
    }
  }

  function removeRestriction(value: string) {
    setRestrictions((current) => current.filter((item) => item !== value))
  }

  function appendContextHint(hint: string) {
    setContext((current) => (current.trim() ? `${current.trim()}\n${hint}: ` : `${hint}: `))
  }

  function handleAttachmentSelection(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? [])
    event.target.value = ''
    if (files.length === 0) return

    const tooLarge = files.filter((file) => file.size > MAX_ATTACHMENT_BYTES)
    const accepted = files.filter((file) => file.size <= MAX_ATTACHMENT_BYTES)
    if (tooLarge.length > 0) {
      setAttachmentWarning(
        `${tooLarge.map((file) => file.name).join(', ')} ${tooLarge.length > 1 ? 'excedem' : 'excede'} ${Math.round(MAX_ATTACHMENT_BYTES / 1000)} KB e não ${tooLarge.length > 1 ? 'foram adicionados' : 'foi adicionado'}.`,
      )
    } else {
      setAttachmentWarning('')
    }
    setAttachments((current) => [...current, ...accepted])
  }

  function removeAttachment(name: string) {
    setAttachments((current) => current.filter((file) => file.name !== name))
  }

  async function handleFinalSubmit() {
    setSubmitting(true)
    setSubmitError('')
    try {
      const created = await orchestrationApi.createRequest({
        title: title.trim(),
        problem: problem.trim(),
        objective: objective.trim(),
        context: context.trim() || null,
        restrictions,
      })

      // The request itself is already created at this point -- an attachment
      // failing (e.g. a duplicate-named file the extension check still
      // rejects for some other reason) shouldn't block navigation or read as
      // "nothing was saved". Failures are collected and surfaced on the
      // orchestration page instead of aborting here.
      const failedUploads: string[] = []
      for (const file of attachments) {
        try {
          await orchestrationApi.uploadAttachment(created.id, file)
        } catch {
          failedUploads.push(file.name)
        }
      }

      navigate(`/orchestrations/${created.trace_id}`, {
        state: failedUploads.length > 0 ? { failedAttachmentUploads: failedUploads } : undefined,
      })
    } catch (caught) {
      setSubmitError(caught instanceof ApiError ? caught.message : 'Não foi possível criar a solicitação.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="workspace-page workspace-page-narrow">
      <section className="workspace-page-heading fade-up">
        <div>
          <span className="workspace-eyebrow">NOVA SOLICITAÇÃO</span>
          <h1>Qualifique uma demanda técnica</h1>
          <p>Esses dados formarão o contexto inicial entregue ao Orientador de Interação.</p>
        </div>
      </section>

      <ol className="workspace-stepper fade-up" style={{ animationDelay: '0.06s' }}>
        {[1, 2, 3].map((index) => {
          const state = index < step ? 'done' : index === step ? 'current' : 'future'
          const labels = ['Identificação', 'Problema & objetivo', 'Contexto & restrições']
          return (
            <li key={index} className={`workspace-step workspace-step-${state}`}>
              <span className={`workspace-step-circle${state === 'current' ? ' pop-in' : ''}`}>
                {state === 'done' ? '✓' : index}
              </span>
              <span className="workspace-step-label">{labels[index - 1]}</span>
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
                Título
                <input
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  minLength={5}
                  maxLength={160}
                  placeholder="Ex.: Erro de timeout no serviço de pagamentos"
                  autoFocus
                />
                <small>Uma identificação curta e específica — evite títulos genéricos como &ldquo;teste&rdquo;.</small>
              </label>
            </div>
          )}

          {step === 2 && (
            <div className="workspace-form-grid">
              <label className="workspace-field workspace-field-full">
                Problema a ser analisado
                <textarea
                  value={problem}
                  onChange={(event) => setProblem(event.target.value)}
                  rows={5}
                  minLength={10}
                  placeholder="Descreva o comportamento atual, a divergência ou a dúvida técnica..."
                  autoFocus
                />
                <small>
                  Exemplo: &ldquo;O endpoint /checkout retorna 504 após ~30s quando o carrinho tem mais de 20 itens.
                  Em produção acontece desde a última implantação.&rdquo;
                </small>
              </label>

              <label className="workspace-field workspace-field-full">
                Objetivo da análise
                <textarea
                  value={objective}
                  onChange={(event) => setObjective(event.target.value)}
                  rows={3}
                  minLength={5}
                  placeholder="Informe qual resposta ou resultado você espera obter..."
                />
                <small>
                  Exemplo: &ldquo;Identificar se o timeout vem do gateway de pagamento ou da nossa API, e propor um
                  limite seguro.&rdquo;
                </small>
              </label>
            </div>
          )}

          {step === 3 && (
            <div className="workspace-form-grid">
              <label className="workspace-field workspace-field-full">
                Contexto técnico
                <textarea
                  value={context}
                  onChange={(event) => setContext(event.target.value)}
                  rows={7}
                  placeholder="Inclua módulos, tecnologias, artefatos, dependências e comportamento esperado..."
                  autoFocus
                />
                <div className="workspace-chip-row">
                  {contextSuggestions.map((hint) => (
                    <button key={hint} type="button" className="workspace-suggestion-chip" onClick={() => appendContextHint(hint)}>
                      {hint}
                    </button>
                  ))}
                </div>
                <small>
                  Inclua módulos, tecnologias, artefatos, dependências e comportamento esperado. Caso seja
                  insuficiente, a solicitação ficará aguardando complementação.
                </small>
              </label>

              <label className="workspace-field workspace-field-full">
                Restrições
                <div className="workspace-tag-input">
                  {restrictions.map((item) => (
                    <span key={item} className="workspace-tag">
                      {item}
                      <button type="button" aria-label={`Remover restrição ${item}`} onClick={() => removeRestriction(item)}>×</button>
                    </span>
                  ))}
                  <input
                    value={restrictionDraft}
                    onChange={(event) => setRestrictionDraft(event.target.value)}
                    onKeyDown={handleRestrictionKeyDown}
                    onBlur={() => addRestriction(restrictionDraft)}
                    placeholder="+ Adicionar restrição"
                  />
                </div>
                <small>Separe restrições por linha ou vírgula — cada uma vira uma tag independente.</small>
              </label>

              <label className="workspace-field workspace-field-full">
                Anexar documento (opcional)
                <label className="workspace-secondary-action workspace-attachment-trigger">
                  + Anexar documento
                  <input
                    type="file"
                    accept={ALLOWED_ATTACHMENT_EXTENSIONS}
                    multiple
                    onChange={handleAttachmentSelection}
                    style={{ display: 'none' }}
                  />
                </label>
                <small>
                  Texto puro (código-fonte, markdown, JSON, etc.) — até {Math.round(MAX_ATTACHMENT_BYTES / 1000)} KB
                  por arquivo. PDF e DOCX ainda não são suportados.
                </small>
                {attachmentWarning && <small style={{ color: 'var(--danger, #ef4444)' }}>{attachmentWarning}</small>}
                {attachments.length > 0 && (
                  <ul className="workspace-tag-input" style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
                    {attachments.map((file) => (
                      <li key={file.name} className="workspace-tag">
                        {file.name}
                        <button type="button" aria-label={`Remover anexo ${file.name}`} onClick={() => removeAttachment(file.name)}>
                          ×
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </label>
            </div>
          )}
        </div>

        <div className="workspace-wizard-side">
          <article className="workspace-panel workspace-panel-secondary">
            <span className="workspace-card-kicker">CHECKLIST DE CONTEXTO</span>
            <ul className="workspace-checklist">
              {checklist.map((item) => (
                <li key={item.key} className={`workspace-checklist-item workspace-checklist-${item.state}`}>
                  <span className={`workspace-checklist-dot${item.state === 'done' ? ' pop-in' : ''}`} aria-hidden="true">
                    {item.state === 'done' ? '✓' : ''}
                  </span>
                  {item.label}
                </li>
              ))}
            </ul>
          </article>

          <article className="workspace-tip-box">
            <span className="workspace-tip-icon" aria-hidden="true">i</span>
            <p>{stepTips[step]}</p>
          </article>
        </div>
      </div>

      {(stepError || submitError) && <div className="alert alert-error">{stepError || submitError}</div>}

      <div className="workspace-wizard-footer">
        {step === 1 ? (
          <button type="button" className="workspace-secondary-action" onClick={() => navigate(-1)}>Cancelar</button>
        ) : (
          <button type="button" className="workspace-secondary-action" onClick={goBack}>← Voltar</button>
        )}

        {step < 3 ? (
          <button type="button" className="workspace-primary-action" onClick={goNext}>Continuar →</button>
        ) : (
          <button type="button" className="workspace-primary-action" onClick={handleFinalSubmit} disabled={submitting}>
            {submitting ? 'Registrando…' : 'Registrar e gerar Trace ID'}
          </button>
        )}
      </div>
    </div>
  )
}
