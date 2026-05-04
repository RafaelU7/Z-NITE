import { useEffect, useState } from 'react'
import { Monitor, User, Clock, Wifi, WifiOff, Receipt, FileText, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { usePDVStore } from '@/store/pdvStore'
import { useNavigate } from 'react-router-dom'
import { useEmpresaNome } from '@/hooks/useEmpresaNome'
import type { SessaoCaixaDTO, TipoEmissao, VendaDTO } from '@/shared/types/api'
import clsx from 'clsx'

interface StatusBarPDVProps {
  sessao: SessaoCaixaDTO | null
  venda: VendaDTO | null
  modoEmissao?: TipoEmissao
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
}

export function StatusBarPDV({ sessao, venda, modoEmissao }: StatusBarPDVProps) {
  const { user } = useAuthStore()
  const { syncEmAndamento } = usePDVStore()
  const navigate = useNavigate()
  const empresaNome = useEmpresaNome()
  const [hora, setHora] = useState(currentTime())
  const [online, setOnline] = useState(navigator.onLine)

  useEffect(() => {
    const tick = setInterval(() => setHora(currentTime()), 10_000)
    return () => clearInterval(tick)
  }, [])

  useEffect(() => {
    const up = () => setOnline(true)
    const down = () => setOnline(false)
    window.addEventListener('online', up)
    window.addEventListener('offline', down)
    return () => {
      window.removeEventListener('online', up)
      window.removeEventListener('offline', down)
    }
  }, [])

  return (
    <div className="flex items-center gap-3 border-b border-white/10 bg-slate-900 px-4 py-2 text-xs shrink-0">
      {/* ── Branding / Empresa ── */}
      <div className="flex flex-col leading-tight min-w-0">
        <span className="font-bold tracking-tight text-white text-sm truncate max-w-[180px]">{empresaNome}</span>
        <span className="text-[10px] text-slate-400 uppercase tracking-widest">Zênite PDV</span>
      </div>

      <div className="h-4 w-px bg-white/15 shrink-0" />

      {/* ── Badge de modo fiscal/gerencial ── */}
      {modoEmissao && (
        <>
          <div
            className={clsx(
              'flex items-center gap-1.5 rounded-md px-2.5 py-1 font-bold uppercase tracking-wider shrink-0',
              modoEmissao === 'FISCAL'
                ? 'bg-blue-500/25 text-blue-300 border border-blue-400/40'
                : 'bg-amber-500/25 text-amber-300 border border-amber-400/40',
            )}
          >
            {modoEmissao === 'FISCAL' ? <Receipt size={11} /> : <FileText size={11} />}
            <span className="text-[10px]">
              {modoEmissao === 'FISCAL' ? 'Fiscal NFC-e' : 'Gerencial'}
            </span>
          </div>
          <div className="h-4 w-px bg-white/15 shrink-0" />
        </>
      )}

      {/* ── Caixa ── */}
      <div className="flex items-center gap-1.5 text-slate-300 shrink-0">
        <Monitor size={12} className={sessao ? 'text-green-400' : 'text-slate-500'} />
        {sessao ? (
          <span className="text-green-400">Caixa Aberto</span>
        ) : (
          <span
            className="cursor-pointer hover:text-white transition-colors"
            onClick={() => navigate('/caixa')}
          >
            Abrir Caixa
          </span>
        )}
      </div>

      {/* ── Operador ── */}
      <div className="flex items-center gap-1.5 text-slate-300 shrink-0">
        <User size={12} />
        <span className="truncate max-w-[100px]">{user?.nome ?? '—'}</span>
        {user?.codigo_operador && (
          <span className="rounded bg-white/10 px-1 font-mono text-slate-400">
            #{user.codigo_operador}
          </span>
        )}
      </div>

      {/* ── Venda atual ── */}
      {venda && (
        <>
          <div className="h-4 w-px bg-white/15 shrink-0" />
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-slate-400">Venda</span>
            <span className="rounded bg-indigo-500/20 px-1.5 font-mono font-semibold text-indigo-300">
              #{venda.numero_venda_local}
            </span>
            <span
              className={clsx(
                'rounded-full px-2 py-0.5 text-[10px] font-medium uppercase',
                venda.status === 'em_aberto'
                  ? 'bg-green-500/20 text-green-400'
                  : venda.status === 'concluida'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-red-500/20 text-red-400',
              )}
            >
              {venda.status}
            </span>
          </div>
        </>
      )}

      {/* ── Spacer ── */}
      <div className="flex-1" />

      {/* ── Indicador de conectividade (3 estados) ── */}
      {syncEmAndamento ? (
        <div className="flex items-center gap-1.5 shrink-0 text-blue-300">
          <Loader2 size={12} className="animate-spin" />
          <span>Sincronizando</span>
        </div>
      ) : online ? (
        <div className="flex items-center gap-1.5 shrink-0 text-green-400">
          <Wifi size={12} />
          <span>Online</span>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 shrink-0 text-red-400">
          <WifiOff size={12} />
          <span>Offline</span>
        </div>
      )}

      <div className="h-4 w-px bg-white/15 shrink-0" />

      {/* ── Relógio ── */}
      <div className="flex items-center gap-1 font-mono text-slate-400 shrink-0">
        <Clock size={12} />
        {hora}
      </div>
    </div>
  )
}

function currentTime(): string {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}
