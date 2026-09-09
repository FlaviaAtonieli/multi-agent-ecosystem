import { KeyboardEvent, useState } from 'react'

interface Props {
  label: string
  hint?: string
  placeholder?: string
  values: string[]
  onChange: (values: string[]) => void
  required?: boolean
}

// Same tag-chip interaction as the "Restrições" field in NewRequestPage --
// reused here so every list field in the skill-creation form (capabilities,
// contracts, etc.) behaves identically instead of reinventing the pattern.
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
