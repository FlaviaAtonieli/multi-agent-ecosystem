import { useEffect, useRef, useState } from 'react'
import { RequestStatus } from '../../api/orchestrationApi'

const statusLabels: Record<RequestStatus, string> = {
  RECEIVED: 'Recebida',
  AWAITING_CONTEXT: 'Aguardando contexto',
  QUALIFIED: 'Qualificada',
  PLANNING: 'Planejando',
  RUNNING: 'Em execução',
  VALIDATING: 'Quality Gate',
  COMPLETED: 'Concluída',
  REJECTED: 'Rejeitada',
  FAILED: 'Falha',
  CANCELLED: 'Cancelada',
}

const statusDescriptions: Record<RequestStatus, string> = {
  RECEIVED: 'A solicitação foi registrada e aguarda a próxima etapa do fluxo.',
  AWAITING_CONTEXT:
    'Falta contexto suficiente para prosseguir — complemente a descrição do problema para qualificar a solicitação.',
  QUALIFIED: 'O contexto foi validado e a solicitação está pronta para ser processada.',
  PLANNING: 'O planejador técnico está montando o plano de análise antes de acionar as Agent Skills.',
  RUNNING: 'As Agent Skills selecionadas estão executando a análise técnica.',
  VALIDATING: 'O Quality Gate está validando as respostas das Agent Skills antes da entrega final.',
  COMPLETED: 'A análise foi concluída e a resposta consolidada está disponível.',
  REJECTED: 'Um revisor humano rejeitou o resultado — veja a justificativa no histórico.',
  FAILED: 'Ocorreu uma falha técnica durante o processamento — veja os detalhes no histórico de eventos.',
  CANCELLED: 'A solicitação foi cancelada antes de ser concluída.',
}

export function StatusBadge({ status }: { status: RequestStatus }) {
  const [open, setOpen] = useState(false)
  const [position, setPosition] = useState<{ top: number; left: number } | null>(null)
  const triggerRef = useRef<HTMLButtonElement>(null)
  const popoverRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node
      if (triggerRef.current?.contains(target) || popoverRef.current?.contains(target)) return
      setOpen(false)
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }

    document.addEventListener('mousedown', handlePointerDown)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mousedown', handlePointerDown)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [open])

  function toggleOpen() {
    if (!open && triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect()
      setPosition({ top: rect.bottom + 8, left: rect.left })
    }
    setOpen((value) => !value)
  }

  return (
    <span className="workspace-status-group">
      <span className={`workspace-status workspace-status-${status.toLowerCase()}`}>{statusLabels[status]}</span>
      <button
        ref={triggerRef}
        type="button"
        className="workspace-status-info-trigger"
        aria-label={`O que significa o status "${statusLabels[status]}"?`}
        aria-expanded={open}
        onClick={toggleOpen}
      >
        !
      </button>
      {open && position && (
        <div
          ref={popoverRef}
          role="tooltip"
          className="workspace-status-info-popover"
          style={{ top: position.top, left: position.left }}
        >
          <strong>{statusLabels[status]}</strong>
          <p>{statusDescriptions[status]}</p>
        </div>
      )}
    </span>
  )
}
