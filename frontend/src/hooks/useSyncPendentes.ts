/**
 * useSyncPendentes — gerencia contagem e disparo manual de sincronização.
 *
 * Atualiza periodicamente o contador de vendas pendentes de sync.
 * Expõe `sincronizarManual()` para reenvio pelo operador.
 */

import { useEffect, useCallback } from 'react'
import { usePDVStore } from '@/store/pdvStore'
import {
  executarSyncPendentes,
  countVendasPendentes,
} from '@/services/offline/syncService'

const POLL_INTERVAL_MS = 8_000

export function useSyncPendentes() {
  const {
    pendentesSync,
    setPendentesSync,
    syncEmAndamento,
    setSyncEmAndamento,
    setUltimoSyncErro,
    ultimoSyncErro,
    isOffline,
  } = usePDVStore()

  const refresh = useCallback(async () => {
    const count = await countVendasPendentes()
    setPendentesSync(count)
  }, [setPendentesSync])

  // Polling periódico do contador
  useEffect(() => {
    void refresh()
    const interval = setInterval(() => void refresh(), POLL_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [refresh])

  const sincronizarManual = useCallback(async () => {
    if (syncEmAndamento || isOffline) return
    setSyncEmAndamento(true)
    setUltimoSyncErro(null)
    try {
      const result = await executarSyncPendentes()
      await refresh()
      return result
    } catch (err) {
      setUltimoSyncErro(err instanceof Error ? err.message : 'Erro de sincronização.')
    } finally {
      setSyncEmAndamento(false)
    }
  }, [syncEmAndamento, isOffline, setSyncEmAndamento, setUltimoSyncErro, refresh])

  return {
    pendentesSync,
    syncEmAndamento,
    ultimoSyncErro,
    refresh,
    sincronizarManual,
  }
}
