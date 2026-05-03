import { useEffect, useState } from 'react'
import { Monitor, User, Clock, Wifi, WifiOff, Receipt, FileText } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
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
    <div className="flex items-center gap-4 border-b border-border bg-bg-surface px-4 py-2 text-xs">
      {/* Branding */}
      <div className="flex flex-col leading-tight min-w-0">
        <span className="font-bold tracking-tight text-text-primary text-sm">{empresaNome}</span>
        <span className="text-[10px] text-text-muted uppercase tracking-wide">Zênite PDV</span>
      </div>

      <div className="h-3 w-px bg-border" />

      {/* Modo fiscal/gerencial */}
      {modoEmissao && (
        <>
          <div
            className={clsx(
              'flex items-center gap-1.5 rounded-md px-2 py-1 font-bold uppercase tracking-wider',
              modoEmissao === 'FISCAL'
                ? 'bg-info/20 text-info-text border border-info/40'
                : 'bg-warning/20 text-warning-text border border-warning/40',
            )}
          >
            {modoEmissao === 'FISCAL' ? <Receipt size={11} /> : <FileText size={11} />}
            <span className="text-[10px]">
              {modoEmissao === 'FISCAL' ? 'Fiscal NFC-e' : 'Gerencial'}
            </span>
          </div>
          <div className="h-3 w-px bg-border" />
        </>
      )}

      {/* Caixa */}
      <div className="flex items-center gap-1.5 text-text-secondary">
        <Monitor size={12} className={sessao ? 'text-success' : 'text-text-muted'} />
        <span>
          {sessao ? (
            <span className="text-success-text">Caixa Aberto</span>
          ) : (
            <span
              className="cursor-pointer hover:text-text-primary"
              onClick={() => navigate('/caixa')}
            >
              Abrir Caixa
            </span>
          )}
        </span>
      </div>

      {/* Operador */}
      <div className="flex items-center gap-1.5 text-text-secondary">
        <User size={12} />
        <span>{user?.nome ?? '—'}</span>
        {user?.codigo_operador && (
          <span className="rounded bg-bg-surface-2 px-1 font-mono text-text-muted">
            #{user.codigo_operador}
          </span>
        )}
      </div>

      {/* Venda atual */}
      {venda && (
        <>
          <div className="h-3 w-px bg-border" />
          <div className="flex items-center gap-1.5">
            <span className="text-text-muted">Venda</span>
            <span className="rounded bg-accent/15 px-1.5 font-mono font-semibold text-accent">
              #{venda.numero_venda_local}
            </span>
            <span
              className={clsx(
                'rounded-full px-2 py-0.5 text-[10px] font-medium uppercase',
                venda.status === 'em_aberto'
                  ? 'bg-success/20 text-success-text'
                  : venda.status === 'concluida'
                    ? 'bg-info/20 text-info-text'
                    : 'bg-danger/20 text-danger-text',
              )}
            >
              {venda.status}
            </span>
          </div>
        </>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Online indicator */}
      <div className={clsx('flex items-center gap-1', online ? 'text-success-text' : 'text-danger-text')}>
        {online ? <Wifi size={12} /> : <WifiOff size={12} />}
        <span>{online ? 'Online' : 'Offline'}</span>
      </div>

      <div className="h-3 w-px bg-border" />

      {/* Relógio */}
      <div className="flex items-center gap-1 font-mono text-text-muted">
        <Clock size={12} />
        {hora}
      </div>
    </div>
  )
}

function currentTime(): string {
  return new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}
