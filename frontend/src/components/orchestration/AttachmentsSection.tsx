import { ChangeEvent, useEffect, useState } from 'react'
import { ApiError } from '../../api/http'
import { orchestrationApi, RequestAttachment } from '../../api/orchestrationApi'

const MAX_ATTACHMENT_BYTES = 300_000
const ALLOWED_ATTACHMENT_EXTENSIONS =
  '.txt,.md,.markdown,.py,.js,.jsx,.ts,.tsx,.java,.go,.rb,.php,.cs,.c,.cpp,.h,.hpp,.kt,.swift,.rs,.json,.yaml,.yml,.xml,.sql,.sh'

function formatSize(bytes: number): string {
  return bytes < 1000 ? `${bytes} B` : `${Math.round(bytes / 1000)} KB`
}

export function AttachmentsSection({ requestId }: { requestId: string }) {
  const [attachments, setAttachments] = useState<RequestAttachment[]>([])
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)

  function load() {
    orchestrationApi
      .listAttachments(requestId)
      .then(setAttachments)
      .catch(() => undefined)
  }

  useEffect(load, [requestId])

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return

    if (file.size > MAX_ATTACHMENT_BYTES) {
      setError(`O arquivo excede ${Math.round(MAX_ATTACHMENT_BYTES / 1000)} KB.`)
      return
    }

    setUploading(true)
    setError('')
    try {
      await orchestrationApi.uploadAttachment(requestId, file)
      load()
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível anexar o arquivo.')
    } finally {
      setUploading(false)
    }
  }

  async function handleRemove(attachmentId: string) {
    setError('')
    try {
      await orchestrationApi.deleteAttachment(requestId, attachmentId)
      setAttachments((current) => current.filter((item) => item.id !== attachmentId))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Não foi possível remover o anexo.')
    }
  }

  return (
    <div className="workspace-field">
      <span>Documentos anexados</span>
      {attachments.length > 0 && (
        <ul className="workspace-tag-input" style={{ listStyle: 'none', padding: 0, margin: '4px 0' }}>
          {attachments.map((attachment) => (
            <li key={attachment.id} className="workspace-tag">
              {attachment.filename}
              <small style={{ marginLeft: 4, opacity: 0.7 }}>({formatSize(attachment.size_bytes)})</small>
              <button
                type="button"
                aria-label={`Remover anexo ${attachment.filename}`}
                onClick={() => handleRemove(attachment.id)}
              >
                ×
              </button>
            </li>
          ))}
        </ul>
      )}
      <label className="workspace-secondary-action" style={{ display: 'inline-flex', cursor: 'pointer' }}>
        {uploading ? 'Enviando…' : '+ Anexar documento'}
        <input
          type="file"
          accept={ALLOWED_ATTACHMENT_EXTENSIONS}
          onChange={handleFileSelected}
          disabled={uploading}
          style={{ display: 'none' }}
        />
      </label>
      {error && <small style={{ color: 'var(--danger, #ef4444)', display: 'block', marginTop: 4 }}>{error}</small>}
    </div>
  )
}
