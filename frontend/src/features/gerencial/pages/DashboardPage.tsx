import { useEffect, useState } from 'react'
import { TrendingUp, ShoppingCart, Receipt, CreditCard, Loader2 } from 'lucide-react'
import { getDashboard } from '@/services/api/gerencial'
import type { DashboardDTO } from '@/shared/types/api'
import { formatCurrency } from '@/shared/utils/format'

export function DashboardPage() {
  const [data, setData] = useState<DashboardDTO | null>(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch(() => setErro('Erro ao carregar dashboard.'))
      .finally(() => setLoading(false))
  }, [])

  if (loading)
    return (
      <div className="flex items-center gap-2 text-text-muted">
        <Loader2 size={18} className="animate-spin" />
        Carregando...
      </div>
    )

  if (erro) return <p className="text-sm text-danger-text">{erro}</p>
  if (!data) return null

  const dateLabel = new Date(data.data_referencia + 'T00:00:00').toLocaleDateString('pt-BR', {
    weekday: 'long',
    day: '2-digit',
    month: 'long',
  })

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-text-primary">Dashboard</h1>
        <p className="text-sm text-text-muted capitalize">{dateLabel}</p>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <KpiCard
          label="Vendas hoje"
          value={formatCurrency(Number(data.total_vendas))}
          icon={<TrendingUp size={18} />}
          color="text-success-text"
          bg="bg-success/10 border-success/30"
        />
        <KpiCard
          label="Qtd. vendas"
          value={String(data.qtd_vendas)}
          icon={<ShoppingCart size={18} />}
          color="text-info-text"
          bg="bg-info/10 border-info/30"
        />
        <KpiCard
          label="Ticket médio"
          value={formatCurrency(Number(data.ticket_medio))}
          icon={<Receipt size={18} />}
          color="text-warning-text"
          bg="bg-warning/10 border-warning/30"
        />
        <KpiCard
          label="Sessões abertas"
          value={String(data.sessoes_abertas)}
          icon={<CreditCard size={18} />}
          color="text-accent"
          bg="bg-accent/10 border-accent/30"
        />
      </div>

      {/* Breakdown por forma de pagamento */}
      {data.por_forma_pagamento.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-surface p-4">
          <h2 className="mb-3 text-sm font-semibold text-text-primary">Por forma de pagamento</h2>
          <div className="flex flex-col gap-2">
            {data.por_forma_pagamento.map((f) => (
              <div
                key={f.forma}
                className="flex items-center justify-between rounded-lg bg-bg-surface-2 px-3 py-2.5 text-sm"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">{f.label}</span>
                  <span className="text-xs text-text-muted">{f.qtd} venda{f.qtd !== 1 ? 's' : ''}</span>
                </div>
                <span className="font-mono font-medium text-text-primary">
                  {formatCurrency(Number(f.total))}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.por_forma_pagamento.length === 0 && (
        <p className="text-sm text-text-muted">Nenhuma venda concluída hoje.</p>
      )}
    </div>
  )
}

function KpiCard({
  label,
  value,
  icon,
  color,
  bg,
}: {
  label: string
  value: string
  icon: React.ReactNode
  color: string
  bg: string
}) {
  return (
    <div className={`flex flex-col gap-1.5 rounded-xl border p-4 ${bg}`}>
      <div className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
        {icon}
        {label}
      </div>
      <p className="font-mono text-2xl font-bold text-text-primary">{value}</p>
    </div>
  )
}
