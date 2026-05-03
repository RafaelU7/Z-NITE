import { useEffect, useState } from 'react'
import {
  TrendingUp, ShoppingCart, Receipt, CreditCard, CalendarDays,
  RefreshCw, Loader2, ChevronDown, ChevronUp, AlertTriangle,
} from 'lucide-react'
import { getRelatorioDiario } from '@/services/api/gerencial'
import type { RelatorioDiarioDTO, SessaoListDTO } from '@/shared/types/api'
import { formatCurrency, formatDateTime } from '@/shared/utils/format'
import clsx from 'clsx'

function hoje(): string {
  return new Date().toISOString().slice(0, 10)
}

function fmtData(iso: string) {
  return new Date(iso + 'T00:00:00').toLocaleDateString('pt-BR', {
    weekday: 'long', day: '2-digit', month: 'long', year: 'numeric',
  })
}

// ---------------------------------------------------------------------------
// Sessão expandível
// ---------------------------------------------------------------------------
function SessaoRow({ s }: { s: SessaoListDTO }) {
  const [aberto, setAberto] = useState(false)
  const isFechada = s.status === 'fechada'
  const dif = Number(s.diferenca_fechamento ?? 0)
  const positivoDif = dif >= 0

  const formas = [
    { label: 'Dinheiro', valor: Number(s.total_dinheiro) },
    { label: 'Pix', valor: Number(s.total_pix) },
    { label: 'Cartão Débito', valor: Number(s.total_cartao_debito) },
    { label: 'Cartão Crédito', valor: Number(s.total_cartao_credito) },
    { label: 'Outros', valor: Number(s.total_outros) },
  ].filter((f) => f.valor > 0)

  return (
    <div className="rounded-xl border border-border bg-bg-surface-2 overflow-hidden">
      <button
        onClick={() => setAberto((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm hover:bg-bg-surface transition-colors"
      >
        <div className="flex items-center gap-3 text-left">
          <span
            className={clsx(
              'rounded-full px-2 py-0.5 text-xs font-medium',
              isFechada ? 'bg-bg-surface-2 text-text-muted border border-border' : 'bg-success/15 text-success-text',
            )}
          >
            {isFechada ? 'FECHADA' : 'ABERTA'}
          </span>
          <div>
            <p className="font-medium text-text-primary">
              {s.caixa_descricao ?? `Caixa ${s.caixa_numero}`}
              <span className="ml-2 font-normal text-text-muted">— {s.operador_nome}</span>
            </p>
            <p className="text-xs text-text-muted">{formatDateTime(s.data_abertura)}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <p className="font-mono font-semibold text-text-primary">{formatCurrency(Number(s.total_liquido))}</p>
            <p className="text-xs text-text-muted">{s.quantidade_vendas} venda{s.quantidade_vendas !== 1 ? 's' : ''}</p>
          </div>
          {aberto ? <ChevronUp size={15} className="text-text-muted" /> : <ChevronDown size={15} className="text-text-muted" />}
        </div>
      </button>

      {aberto && (
        <div className="border-t border-border px-4 py-3 text-sm">
          <div className="grid grid-cols-2 gap-x-6 gap-y-1.5">
            {isFechada && (
              <>
                <span className="text-text-muted">Esperado dinheiro</span>
                <span className="font-mono text-text-secondary text-right">{formatCurrency(Number(s.saldo_sistema_fechamento ?? 0))}</span>
                <span className="text-text-muted">Contado dinheiro</span>
                <span className="font-mono text-text-secondary text-right">{formatCurrency(Number(s.saldo_informado_fechamento ?? 0))}</span>
                <span className="text-text-muted font-medium">Diferença</span>
                <span className={clsx('font-mono font-semibold text-right', positivoDif ? 'text-success-text' : 'text-danger-text')}>
                  {positivoDif ? '+' : ''}{formatCurrency(dif)}
                </span>
              </>
            )}
            {formas.map((f) => (
              <>
                <span key={f.label + '-l'} className="text-text-muted">{f.label}</span>
                <span key={f.label + '-v'} className="font-mono text-text-secondary text-right">{formatCurrency(f.valor)}</span>
              </>
            ))}
            {s.ticket_medio && (
              <>
                <span className="text-text-muted">Ticket médio</span>
                <span className="font-mono text-text-secondary text-right">{formatCurrency(Number(s.ticket_medio))}</span>
              </>
            )}
            {s.data_fechamento && (
              <>
                <span className="text-text-muted">Fechamento</span>
                <span className="text-text-secondary text-right">{formatDateTime(s.data_fechamento)}</span>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Página
// ---------------------------------------------------------------------------
export function RelatorioDiarioPage() {
  const [data, setData] = useState(hoje())
  const [relatorio, setRelatorio] = useState<RelatorioDiarioDTO | null>(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')

  async function carregar(d: string) {
    setLoading(true)
    setErro('')
    try {
      setRelatorio(await getRelatorioDiario(d))
    } catch {
      setErro('Erro ao carregar relatório.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { carregar(data) }, [data])

  const difTotal = Number(relatorio?.diferenca_total ?? 0)
  const difPositivo = difTotal >= 0

  const dateLabel = relatorio ? fmtData(relatorio.data_referencia) : ''

  return (
    <div className="flex flex-col gap-6">
      {/* Cabeçalho */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">Relatório Diário</h1>
          <p className="text-sm text-text-muted capitalize">{dateLabel}</p>
        </div>
        <div className="flex items-center gap-2">
          <input
            type="date"
            value={data}
            max={hoje()}
            onChange={(e) => setData(e.target.value)}
            className="rounded-lg border border-border bg-bg-surface px-3 py-1.5 text-sm text-text-primary focus:border-accent focus:outline-none"
          />
          <button
            onClick={() => carregar(data)}
            className="flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-sm text-text-secondary hover:bg-bg-surface-2 transition-colors"
          >
            <RefreshCw size={14} />
            Atualizar
          </button>
        </div>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-text-muted">
          <Loader2 size={18} className="animate-spin" /> Carregando...
        </div>
      )}
      {erro && <p className="text-sm text-danger-text">{erro}</p>}

      {relatorio && !loading && (
        <>
          {/* KPIs */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <KpiCard
              label="Total Vendido"
              value={formatCurrency(Number(relatorio.total_vendas))}
              icon={<TrendingUp size={16} />}
              color="text-success-text"
              bg="bg-success/10 border-success/30"
            />
            <KpiCard
              label="Qtd. Vendas"
              value={String(relatorio.qtd_vendas)}
              icon={<ShoppingCart size={16} />}
              color="text-info-text"
              bg="bg-info/10 border-info/30"
            />
            <KpiCard
              label="Ticket Médio"
              value={formatCurrency(Number(relatorio.ticket_medio))}
              icon={<Receipt size={16} />}
              color="text-warning-text"
              bg="bg-warning/10 border-warning/30"
            />
            <KpiCard
              label="Sessões"
              value={`${relatorio.sessoes_abertas} aberta${relatorio.sessoes_abertas !== 1 ? 's' : ''} / ${relatorio.sessoes_fechadas} fechada${relatorio.sessoes_fechadas !== 1 ? 's' : ''}`}
              icon={<CreditCard size={16} />}
              color="text-accent"
              bg="bg-accent/10 border-accent/30"
            />
          </div>

          {/* Diferença total */}
          <div className={clsx(
            'flex items-center justify-between rounded-xl border px-4 py-3',
            difPositivo ? 'border-success/30 bg-success/10' : 'border-danger/30 bg-danger/10',
          )}>
            <div className="flex items-center gap-2">
              <AlertTriangle size={16} className={difPositivo ? 'text-success-text' : 'text-danger-text'} />
              <span className={clsx('text-sm font-medium', difPositivo ? 'text-success-text' : 'text-danger-text')}>
                Diferença total de caixa (sessões fechadas)
              </span>
            </div>
            <span className={clsx('font-mono font-bold text-lg', difPositivo ? 'text-success-text' : 'text-danger-text')}>
              {difPositivo ? '+' : ''}{formatCurrency(difTotal)}
            </span>
          </div>

          {/* Por forma de pagamento */}
          {relatorio.por_forma_pagamento.length > 0 && (
            <div className="rounded-xl border border-border bg-bg-surface p-4">
              <div className="flex items-center gap-1.5 text-xs text-text-muted mb-3">
                <CalendarDays size={14} /> Por forma de pagamento
              </div>
              <div className="flex flex-col gap-2">
                {relatorio.por_forma_pagamento.map((f) => (
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

          {/* Sessões */}
          <div>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-text-muted">
              Sessões do dia ({relatorio.sessoes.length})
            </h2>
            {relatorio.sessoes.length === 0 ? (
              <p className="text-sm text-text-muted">Nenhuma sessão encontrada para esta data.</p>
            ) : (
              <div className="flex flex-col gap-2">
                {relatorio.sessoes.map((s) => (
                  <SessaoRow key={s.id} s={s} />
                ))}
              </div>
            )}
          </div>
        </>
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
    <div className={`rounded-xl border p-4 ${bg}`}>
      <div className={`flex items-center gap-1.5 text-xs mb-1 ${color}`}>
        {icon}
        {label}
      </div>
      <p className="font-mono text-lg font-bold text-text-primary leading-tight">{value}</p>
    </div>
  )
}
