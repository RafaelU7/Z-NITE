/**
 * FiscalStatusBadge — exibe o status de emissão fiscal com polling automático.
 *
 * Polling:
 *   - Enquanto status for 'pendente', consulta a cada 3 segundos
 *   - Para quando atingir estado terminal (emitida / rejeitada / erro / cancelada)
 *   - Máximo de 40 tentativas (~2 minutos)
 */
import { useEffect, useRef, useState } from 'react'
import { getStatusDocumento } from '@/services/api/fiscal'
import type { StatusDocumentoFiscal, DocumentoFiscalDTO } from '@/shared/types/api'
import clsx from 'clsx'

const TERMINAL_STATUSES: StatusDocumentoFiscal[] = [
  'emitida',
  'cancelada',
  'rejeitada',
  'inutilizada',
]

const BADGE_CONFIG: Record<
  StatusDocumentoFiscal,
  { label: string; class: string }
> = {
  pendente: {
    label: 'Emitindo NFC-e…',
    class: 'bg-warning-subtle text-warning-text border-warning',
  },
  emitida: {
    label: 'NFC-e Autorizada',
    class: 'bg-success-subtle text-success-text border-success',
  },
  cancelada: {
    label: 'NFC-e Cancelada',
    class: 'bg-bg-surface-3 text-text-secondary border-border',
  },
  rejeitada: {
    label: 'NFC-e Rejeitada',
    class: 'bg-danger-subtle text-danger-text border-danger',
  },
  em_contingencia: {
    label: 'Em Contingência',
    class: 'bg-warning-subtle text-warning-text border-warning',
  },
  inutilizada: {
    label: 'Numeração Inutilizada',
    class: 'bg-bg-surface-3 text-text-secondary border-border',
  },
  erro: {
    label: 'Erro na Emissão',
    class: 'bg-danger-subtle text-danger-text border-danger',
  },
}

interface FiscalStatusBadgeProps {
  documentoFiscalId: string
  /** Callback chamado quando o documento for autorizado */
  onEmitida?: (doc: DocumentoFiscalDTO) => void
}

export function FiscalStatusBadge({ documentoFiscalId, onEmitida }: FiscalStatusBadgeProps) {
  const [doc, setDoc] = useState<DocumentoFiscalDTO | null>(null)
  const [error, setError] = useState(false)
  const pollingCount = useRef(0)
  const MAX_POLLS = 40

  useEffect(() => {
    let cancelled = false

    async function poll() {
      try {
        const result = await getStatusDocumento(documentoFiscalId)
        if (cancelled) return
        setDoc(result)

        if (result.status === 'emitida' && onEmitida) {
          onEmitida(result)
        }

        const isTerminal = TERMINAL_STATUSES.includes(result.status)
        pollingCount.current += 1

        if (!isTerminal && pollingCount.current < MAX_POLLS) {
          setTimeout(poll, 3000)
        }
      } catch {
        if (!cancelled) setError(true)
      }
    }

    poll()
    return () => {
      cancelled = true
    }
  }, [documentoFiscalId, onEmitida])

  if (error) {
    return (
      <div className="rounded-lg border border-danger bg-danger-subtle px-3 py-2 text-sm text-danger-text">
        Não foi possível verificar o status fiscal.
      </div>
    )
  }

  if (!doc) {
    return (
      <div className="flex items-center gap-2 rounded-lg border border-border bg-bg-surface-2 px-3 py-2 text-sm text-text-secondary">
        <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-text-secondary border-t-transparent" />
        Verificando status fiscal…
      </div>
    )
  }

  const config = BADGE_CONFIG[doc.status] ?? {
    label: doc.status,
    class: 'bg-bg-surface-2 text-text-secondary border-border',
  }

  const isPending = doc.status === 'pendente' || doc.status === 'em_contingencia'

  return (
    <div
      className={clsx(
        'flex flex-col gap-1 rounded-lg border px-3 py-2 text-sm',
        config.class,
      )}
    >
      <div className="flex items-center gap-2 font-medium">
        {isPending && (
          <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
        )}
        <span>{config.label}</span>
      </div>

      {doc.chave_acesso && (
        <span className="font-mono text-xs opacity-70">
          Chave: {doc.chave_acesso}
        </span>
      )}

      {doc.protocolo_autorizacao && (
        <span className="text-xs opacity-70">
          Protocolo: {doc.protocolo_autorizacao}
        </span>
      )}

      {doc.mensagem_retorno && doc.status !== 'emitida' && (
        <span className="text-xs opacity-80">{doc.mensagem_retorno}</span>
      )}

      {doc.url_danfe && (
        <a
          href={doc.url_danfe}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 text-xs underline opacity-80 hover:opacity-100"
        >
          Imprimir DANFE
        </a>
      )}
    </div>
  )
}
