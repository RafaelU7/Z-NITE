/**
 * useConnectivity — monitora eventos online/offline do navegador.
 *
 * Deve ser montado UMA vez na raiz da aplicação (PDVPage ou App).
 * Atualiza o store Zustand e dispara sincronização automática ao reconectar.
 */

import { useEffect, useRef } from 'react'
import { usePDVStore } from '@/store/pdvStore'
import {
  executarSyncPendentes,
  countVendasPendentes,
} from '@/services/offline/syncService'

export function useConnectivity() {
  const {
    setIsOffline,
    setSyncEmAndamento,
    setPendentesSync,
    setUltimoSyncErro,
  } = usePDVStore()

  // Ref para evitar múltiplos syncs simultâneos ao reagir a eventos
  const syncingRef = useRef(false)

  useEffect(() => {
    // Inicializa com estado atual
    setIsOffline(!navigator.onLine)

    const handleOnline = async () => {
      setIsOffline(false)
      if (syncingRef.current) return
      syncingRef.current = true
      setSyncEmAndamento(true)
      setUltimoSyncErro(null)
      try {
        await executarSyncPendentes()
        setPendentesSync(await countVendasPendentes())
      } catch (err) {
        setUltimoSyncErro(
          err instanceof Error ? err.message : 'Erro ao sincronizar.',
        )
      } finally {
        setSyncEmAndamento(false)
        syncingRef.current = false
      }
    }

    const handleOffline = () => setIsOffline(true)

    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
}
