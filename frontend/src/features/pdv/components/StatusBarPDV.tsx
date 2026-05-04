import { useEffect, useState } from 'react'
import { User, Clock, Wifi, WifiOff, Receipt, FileText, Loader2 } from 'lucide-react'
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
    <div
      className={clsx(
        'flex items-center gap-3 border-b px-4 py-0 text-xs shrink-0 transition-colors duration-300',
        modoEmissao === 'FISCAL'
          ? 'bg-slate-900 border-emerald-900/60'
          : 'bg-slate-900 border-amber-900/60',
      )}
    >
      {/* ── Branding / Empresa ── */}
      <div className="flex flex-col leading-tight min-w-0 py-2">
        <span className="font-bold tracking-tight text-white text-sm truncate max-w-[180px]">{empresaNome}</span>
        <span className="text-[9px] text-slate-500 uppercase tracking-widest">Zênite PDV</span>
      </div>

      <div className="h-5 w-px bg-white/10 shrink-0" />

      {/* ── Badge de modo fiscal/gerencial — identidade visual principal ── */}
      {modoEmissao && (
        <>
          <div
            className={clsx(
              'flex items-center gap-1.5 rounded-md px-3 py-1.5 font-bold uppercase tracking-widest shrink-0 text-[11px]',
              modoEmissao === 'FISCAL'
                ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                : 'bg-amber-500/20 text-amber-300 border border-amber-500/30',
            )}
          >
            {modoEmissao === 'FISCAL' ? <Receipt size={12} /> : <FileText size={12} />}
            {modoEmissao === 'FISCAL' ? 'FISCAL NFC-E' : 'GERENCIAL'}
          </div>
          <div className="h-5 w-px bg-white/10 shrink-0" />
        </>
      )}

      {/* ── Caixa ── */}
      <div className="flex items-center gap-1.5 shrink-0">
        <div className={clsx('h-1.5 w-1.5 rounded-full', sessao ? 'bg-emerald-400' : 'bg-slate-600')} />
        {sessao ? (
          <span className="text-slate-300">Caixa Aberto</span>
        ) : (
          <span
            className="text-slate-400 cursor-pointer hover:text-white transition-colors"
            onClick={() => navigate('/caixa')}
          >
            Abrir Caixa
          </span>
        )}
      </div>

      {/* ── Operador ── */}
      <div className="flex items-center gap-1.5 text-slate-400 shrink-0">
        <User size={11} />
        <span className="truncate max-w-[100px]">{user?.nome ?? '—'}</span>
        {user?.codigo_operador && (
          <span className="rounded bg-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
            #{user.codigo_operador}
          </span>
        )}
      </div>

      {/* ── Venda atual ── */}
      {venda && (
        <>
          <div className="h-5 w-px bg-white/10 shrink-0" />
          <div className="flex items-center gap-1.5 shrink-0">
            <span className="text-slate-500">Venda</span>
            <span
              className={clsx(
                'rounded px-1.5 py-0.5 font-mono font-semibold text-[11px]',
                modoEmissao === 'FISCAL'
                  ? 'bg-emerald-500/15 text-emerald-300'
                  : 'bg-amber-500/15 text-amber-300',
              )}
            >
              #{venda.numero_venda_local}
            </span>
            <span
              className={clsx(
                'rounded-full px-2 py-0.5 text-[9px] font-semibold uppercase tracking-wider',
                venda.status === 'em_aberto'
                  ? 'bg-emerald-500/15 text-emerald-400'
                  : venda.status === 'concluida'
                    ? 'bg-blue-500/15 text-blue-300'
                    : 'bg-red-500/15 text-red-400',
              )}
            >
              {venda.status}
            </span>
          </div>
        </>
      )}

      {/* ── Spacer ── */}
      <div className="flex-1" />

      {/* ── Indicador de conectividade ── */}
      {syncEmAndamento ? (
        <div className="flex items-center gap-1.5 shrink-0 text-blue-300">
          <Loader2 size={11} className="animate-spin" />
          <span>Sincronizando</span>
        </div>
      ) : online ? (
        <div className="flex items-center gap-1.5 shrink-0 text-slate-500">
          <Wifi size={11} />
          <span>Online</span>
        </div>
      ) : (
        <div className="flex items-center gap-1.5 shrink-0 text-red-400">
          <WifiOff size={11} />
          <span>Offline</span>
        </div>
      )}

      <div className="h-5 w-px bg-white/10 shrink-0" />

      {/* ── Relógio ── */}
      <div className="flex items-center gap-1 font-mono text-slate-400 shrink-0 text-[11px] py-2">
        <Clock size={11} />
        {hora}
      </div>
    </div>
  )
}

function currentTime(): string {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}
