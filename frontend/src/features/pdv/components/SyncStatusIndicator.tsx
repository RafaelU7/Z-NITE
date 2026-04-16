/**
 * SyncStatusIndicator — indicador de vendas pendentes de sincronização.
 *
 * Exibido na toolbar do PDV quando há vendas offline aguardando sync.
 * Inclui botão de reenvio manual e feedback de erros.
 */

import { RefreshCw, AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { useSyncPendentes } from '@/hooks/useSyncPendentes'

export function SyncStatusIndicator() {
  const {
    pendentesSync,
    syncEmAndamento,
    ultimoSyncErro,
    sincronizarManual,
  } = useSyncPendentes()

  // Nada a mostrar se não há pendentes nem erros
  if (pendentesSync === 0 && !syncEmAndamento && !ultimoSyncErro) return null

  return (
    <div className="flex items-center gap-1.5">
      {syncEmAndamento ? (
        <div className="flex items-center gap-1.5 rounded-md border border-info/40 bg-info/10 px-2.5 py-1 text-xs text-info-text">
          <Loader2 size={12} className="animate-spin" />
          <span>Sincronizando...</span>
        </div>
      ) : ultimoSyncErro ? (
        <button
          onClick={() => void sincronizarManual()}
          title={ultimoSyncErro}
          className="flex items-center gap-1.5 rounded-md border border-danger/40 bg-danger/10 px-2.5 py-1 text-xs text-danger-text hover:bg-danger/20 transition-colors"
        >
          <AlertTriangle size={12} />
          <span>Erro — Reenviar ({pendentesSync})</span>
        </button>
      ) : pendentesSync > 0 ? (
        <button
          onClick={() => void sincronizarManual()}
          className={clsx(
            'flex items-center gap-1.5 rounded-md border px-2.5 py-1 text-xs transition-colors',
            'border-amber-500/40 bg-amber-500/10 text-amber-200 hover:bg-amber-500/20',
          )}
        >
          <RefreshCw size={12} />
          <span>
            {pendentesSync} venda{pendentesSync > 1 ? 's' : ''} pendente{pendentesSync > 1 ? 's' : ''}
          </span>
        </button>
      ) : (
        <div className="flex items-center gap-1 text-xs text-success-text">
          <CheckCircle2 size={12} />
          <span>Sincronizado</span>
        </div>
      )}
    </div>
  )
}
