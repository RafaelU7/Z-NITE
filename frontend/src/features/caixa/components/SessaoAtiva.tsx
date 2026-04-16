import { formatDateTime, formatCurrency } from '@/shared/utils/format'
import type { SessaoCaixaDTO } from '@/shared/types/api'
import { Monitor, Clock, DollarSign, TrendingUp, ShoppingCart } from 'lucide-react'
import clsx from 'clsx'

interface SessaoAtivaProps {
  sessao: SessaoCaixaDTO
}

export function SessaoAtiva({ sessao }: SessaoAtivaProps) {
  const isAberta = sessao.status === 'aberta'

  return (
    <div className="rounded-xl border border-border bg-bg-surface-2 p-5">
      <div className="mb-4 flex items-center gap-2">
        <Monitor size={16} className={isAberta ? 'text-success' : 'text-text-muted'} />
        <span className="text-sm font-semibold text-text-primary">Sessão de Caixa</span>
        <span
          className={clsx(
            'ml-auto rounded-full px-2.5 py-0.5 text-xs font-medium',
            isAberta
              ? 'bg-success/20 text-success-text'
              : 'bg-text-muted/10 text-text-muted',
          )}
        >
          {isAberta ? 'ABERTA' : 'FECHADA'}
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-sm">
        <MetaItem
          icon={<Clock size={13} />}
          label="Abertura"
          value={formatDateTime(sessao.data_abertura)}
        />
        <MetaItem
          icon={<DollarSign size={13} />}
          label="Fundo de troco"
          value={formatCurrency(sessao.saldo_abertura)}
        />
        <MetaItem
          icon={<ShoppingCart size={13} />}
          label="Vendas"
          value={String(sessao.quantidade_vendas)}
        />
        <MetaItem
          icon={<TrendingUp size={13} />}
          label="Total líquido"
          value={formatCurrency(sessao.total_liquido)}
        />
      </div>
    </div>
  )
}

function MetaItem({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode
  label: string
  value: string
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="flex items-center gap-1 text-xs text-text-muted">
        {icon}
        {label}
      </span>
      <span className="font-medium text-text-primary">{value}</span>
    </div>
  )
}
