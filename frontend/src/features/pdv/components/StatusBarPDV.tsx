import { useEffect, useState } from 'react'
import { Monitor, User, Clock, Wifi, WifiOff } from 'lucide-react'
import { useAuthStore } from '@/store/authStore'
import { useNavigate } from 'react-router-dom'
import type { SessaoCaixaDTO, VendaDTO } from '@/shared/types/api'
import clsx from 'clsx'

interface StatusBarPDVProps {
  sessao: SessaoCaixaDTO | null
  venda: VendaDTO | null
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
}

export function StatusBarPDV({ sessao, venda }: StatusBarPDVProps) {
  const { user } = useAuthStore()
  const navigate = useNavigate()
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
      <span className="font-bold tracking-tight text-accent">ZÊNITE PDV</span>

      <div className="h-3 w-px bg-border" />

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
