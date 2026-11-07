import { KeyboardEvent, useState } from 'react'

interface Props {
  label: string
  hint?: string
  placeholder?: string
  values: string[]
  onChange: (values: string[]) => void
  required?: boolean
}

// Mesma interação de etiquetas do campo "Restrições" da NewRequestPage, para todo
// campo de lista do formulário de skill funcionar igual.
export function TagListField({ label, hint, placeholder, values, onChange, required }: Props) {
  const [draft, setDraft] = useState('')

  function add(raw: string) {
    const value = raw.trim()
    if (!value) return
    if (!values.includes(value)) onChange([...values, value])
    setDraft('')
  }

  function remove(value: string) {
    onChange(values.filter((item) => item !== value))
  }

  function handleKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault()
      add(draft)
    }
  }

  return (
    <label className="workspace-field workspace-field-full">
      <span className="workspace-field-label-row">
        {label}
        {required && <span className="workspace-field-required">obrigatório</span>}
      </span>
      <div className="workspace-tag-input">
        {values.map((item) => (
          <span key={item} className="workspace-tag">
            {item}
            <button type="button" aria-label={`Remover ${item}`} onClick={() => remove(item)}>×</button>
          </span>
        ))}
        <input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={handleKeyDown}
          onBlur={() => add(draft)}
          placeholder={values.length === 0 ? placeholder : 'Adicionar outro…'}
        />
      </div>
      {hint && <small>{hint}</small>}
    </label>
  )
}
