import { useEffect, useState } from 'react'
import { TrendingUp, ShoppingCart, Receipt, CreditCard, CalendarDays, Calendar, Users, FileText, Loader2 } from 'lucide-react'
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

      {/* KPIs — Hoje */}
      <div>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wider text-text-muted">Hoje</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <KpiCard label="Vendas" value={formatCurrency(Number(data.total_vendas))} icon={<TrendingUp size={16} />} color="text-success-text" bg="bg-success/10 border-success/30" />
          <KpiCard label="Qtd. vendas" value={String(data.qtd_vendas)} icon={<ShoppingCart size={16} />} color="text-info-text" bg="bg-info/10 border-info/30" />
          <KpiCard label="Ticket médio" value={formatCurrency(Number(data.ticket_medio))} icon={<Receipt size={16} />} color="text-warning-text" bg="bg-warning/10 border-warning/30" />
          <KpiCard label="Sessões abertas" value={String(data.sessoes_abertas)} icon={<CreditCard size={16} />} color="text-accent" bg="bg-accent/10 border-accent/30" />
        </div>
      </div>

      {/* Semana / Mês */}
      <div className="grid grid-cols-2 gap-3">
        <div className="rounded-xl border border-border bg-bg-surface p-4">
          <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
            <CalendarDays size={14} /> Últimos 7 dias
          </div>
          <p className="font-mono text-xl font-bold text-text-primary">{formatCurrency(Number(data.total_semana))}</p>
          <p className="text-xs text-text-muted mt-0.5">{data.qtd_semana} vendas</p>
        </div>
        <div className="rounded-xl border border-border bg-bg-surface p-4">
          <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
            <Calendar size={14} /> Este mês
          </div>
          <p className="font-mono text-xl font-bold text-text-primary">{formatCurrency(Number(data.total_mes))}</p>
          <p className="text-xs text-text-muted mt-0.5">{data.qtd_mes} vendas</p>
        </div>
      </div>

      {/* Fiscal vs Gerencial */}
      <div className="rounded-xl border border-border bg-bg-surface p-4">
        <div className="flex items-center gap-1.5 text-xs text-text-muted mb-3">
          <FileText size={14} /> Fiscal vs Gerencial (hoje)
        </div>
        <div className="flex gap-4">
          <div>
            <p className="text-xs text-text-muted">Fiscal (NFC-e)</p>
            <p className="font-mono font-semibold text-text-primary">{formatCurrency(Number(data.total_fiscal))}</p>
          </div>
          <div>
            <p className="text-xs text-text-muted">Gerencial</p>
            <p className="font-mono font-semibold text-text-primary">{formatCurrency(Number(data.total_gerencial))}</p>
          </div>
        </div>
      </div>

      {/* Por operador */}
      {data.por_operador.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-surface p-4">
          <div className="flex items-center gap-1.5 text-xs text-text-muted mb-3">
            <Users size={14} /> Por operador (hoje)
          </div>
          <div className="flex flex-col gap-2">
            {data.por_operador.map((op) => (
              <div key={op.operador_id} className="flex items-center justify-between rounded-lg bg-bg-surface-2 px-3 py-2 text-sm">
                <div>
                  <span className="font-medium text-text-primary">{op.nome}</span>
                  <span className="ml-2 text-xs text-text-muted">{op.qtd} venda{op.qtd !== 1 ? 's' : ''}</span>
                </div>
                <span className="font-mono font-medium text-text-primary">{formatCurrency(op.total)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Breakdown por forma de pagamento */}
      {data.por_forma_pagamento.length > 0 && (
        <div className="rounded-xl border border-border bg-bg-surface p-4">
          <p className="mb-3 text-xs text-text-muted">Por forma de pagamento (hoje)</p>
          <div className="flex flex-col gap-2">
            {data.por_forma_pagamento.map((f) => (
              <div key={f.forma} className="flex items-center justify-between rounded-lg bg-bg-surface-2 px-3 py-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">{f.label}</span>
                  <span className="text-xs text-text-muted">{f.qtd} venda{f.qtd !== 1 ? 's' : ''}</span>
                </div>
                <span className="font-mono font-medium text-text-primary">{formatCurrency(Number(f.total))}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {data.qtd_vendas === 0 && (
        <p className="text-sm text-text-muted">Nenhuma venda concluída hoje.</p>
      )}
    </div>
  )
}

function KpiCard({
  label, value, icon, color, bg,
}: {
  label: string; value: string; icon: React.ReactNode; color: string; bg: string
}) {
  return (
    <div className={`flex flex-col gap-1.5 rounded-xl border p-3 ${bg}`}>
      <div className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
        {icon} {label}
      </div>
      <p className="font-mono text-xl font-bold text-text-primary">{value}</p>
    </div>
  )
}
