/**
 * Banner visível quando o PDV está em modo offline.
 * Posicionado abaixo da StatusBar para máxima visibilidade.
 */

import { WifiOff } from 'lucide-react'

export function OfflineBanner() {
  return (
    <div className="flex items-center justify-center gap-2 bg-amber-500/20 border-b border-amber-500/40 px-4 py-1.5 text-xs font-semibold text-amber-200">
      <WifiOff size={13} className="shrink-0" />
      <span>MODO OFFLINE — as vendas serão sincronizadas automaticamente ao reconectar</span>
    </div>
  )
}
