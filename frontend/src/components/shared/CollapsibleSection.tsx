import { ReactNode, useState } from 'react'

interface Props {
  title: string
  subtitle?: string
  defaultOpen?: boolean
  children: ReactNode
}

export function CollapsibleSection({ title, subtitle, defaultOpen = true, children }: Props) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div className={`workspace-collapsible${open ? ' is-open' : ''}`}>
      <button
        type="button"
        className="workspace-collapsible-header"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
      >
        <span className="workspace-collapsible-title">
          {title}
          {subtitle && <small>{subtitle}</small>}
        </span>
        <span className="workspace-collapsible-toggle" aria-hidden="true">
          {open ? '▾' : '▸'}
        </span>
      </button>
      {open && <div className="workspace-collapsible-body">{children}</div>}
    </div>
  )
}
