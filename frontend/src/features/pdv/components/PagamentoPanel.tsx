import { useState } from 'react'
import { DollarSign, QrCode, CreditCard, Banknote, MoreHorizontal, Check, Loader2, FileText, Receipt } from 'lucide-react'
import { Button } from '@/shared/ui/Button'
import { formatCurrency } from '@/shared/utils/format'
import type { FormaPagamento, TipoEmissao, VendaDTO } from '@/shared/types/api'
import clsx from 'clsx'

interface PagamentoPanelProps {
  venda: VendaDTO
  totalPago: number
  onPagar: (forma: FormaPagamento, valor: number) => Promise<void>
  modoEmissaoSelecionado: TipoEmissao
  onSelecionarModoEmissao: (modo: TipoEmissao) => void
  onFinalizarFiscal: () => Promise<void>
  onFinalizarGerencial: () => Promise<void>
  onScannerFocusChange: (enabled: boolean) => void
  loadingFinalizar?: boolean
}

interface FormaInfo {
  key: FormaPagamento
  label: string
  icon: React.ReactNode
  color: string
}

const FORMAS: FormaInfo[] = [
  {
    key: '01',
    label: 'Dinheiro',
    icon: <Banknote size={18} />,
    color: 'border-success/40 bg-success/10 hover:bg-success/20 text-success-text',
  },
  {
    key: '17',
    label: 'Pix',
    icon: <QrCode size={18} />,
    color: 'border-info/40 bg-info/10 hover:bg-info/20 text-info-text',
  },
  {
    key: '04',
    label: 'Débito',
    icon: <CreditCard size={18} />,
    color: 'border-accent/40 bg-accent/10 hover:bg-accent/20 text-accent-hover',
  },
  {
    key: '03',
    label: 'Crédito',
    icon: <CreditCard size={18} />,
    color: 'border-warning/40 bg-warning/10 hover:bg-warning/20 text-warning-text',
  },
  {
    key: '99',
    label: 'Outros',
    icon: <MoreHorizontal size={18} />,
    color: 'border-border bg-bg-surface-3 hover:bg-bg-surface-2 text-text-secondary',
  },
]

export function PagamentoPanel({
  venda,
  totalPago,
  onPagar,
  modoEmissaoSelecionado,
  onSelecionarModoEmissao,
  onFinalizarFiscal,
  onFinalizarGerencial,
  onScannerFocusChange,
  loadingFinalizar,
}: PagamentoPanelProps) {
  const [formaSelecionada, setFormaSelecionada] = useState<FormaPagamento | null>(null)
  const [valorInput, setValorInput] = useState('')
  const [loadingPagamento, setLoadingPagamento] = useState(false)
  const [erro, setErro] = useState('')

  const totalLiquido = parseFloat(venda.total_liquido)
  const restante = Math.max(0, totalLiquido - totalPago)
  const podeFinalizar = totalPago >= totalLiquido && venda.itens.filter((i) => !i.cancelado).length > 0

  function handleSelecionarForma(forma: FormaPagamento) {
    setFormaSelecionada(forma)
    onScannerFocusChange(false)
    // Sugere o valor restante automaticamente
    setValorInput(restante > 0 ? restante.toFixed(2).replace('.', ',') : '')
    setErro('')
  }

  async function handleConfirmarPagamento() {
    if (!formaSelecionada) return
    const valor = parseFloat(valorInput.replace(',', '.'))
    if (!valor || valor <= 0) {
      setErro('Informe um valor válido.')
      return
    }
    setLoadingPagamento(true)
    setErro('')
    try {
      await onPagar(formaSelecionada, valor)
      setFormaSelecionada(null)
      setValorInput('')
      onScannerFocusChange(true)
    } catch {
      setErro('Erro ao registrar pagamento.')
    } finally {
      setLoadingPagamento(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-xl border border-border bg-bg-surface-2 p-3">
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-muted">
          Tipo de Finalização
        </p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => onSelecionarModoEmissao('FISCAL')}
            className={clsx(
              'rounded-lg border px-3 py-2 text-left transition-colors',
              modoEmissaoSelecionado === 'FISCAL'
                ? 'border-info/40 bg-info/10 text-info-text'
                : 'border-border bg-bg-surface hover:bg-bg-surface-3 text-text-secondary',
            )}
          >
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Receipt size={16} />
              Fiscal
            </div>
            <p className="mt-1 text-xs opacity-80">Gera NFC-e</p>
          </button>
          <button
            type="button"
            onClick={() => onSelecionarModoEmissao('GERENCIAL')}
            className={clsx(
              'rounded-lg border px-3 py-2 text-left transition-colors',
              modoEmissaoSelecionado === 'GERENCIAL'
                ? 'border-warning/40 bg-warning/10 text-warning-text'
                : 'border-border bg-bg-surface hover:bg-bg-surface-3 text-text-secondary',
            )}
          >
            <div className="flex items-center gap-2 text-sm font-semibold">
              <FileText size={16} />
              Gerencial
            </div>
            <p className="mt-1 text-xs opacity-80">Sem valor fiscal</p>
          </button>
        </div>
      </div>

      {/* Formas de pagamento */}
      <div>
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-text-muted">
          Forma de Pagamento
        </p>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {FORMAS.map((f) => (
            <button
              key={f.key}
              onClick={() => handleSelecionarForma(f.key)}
              className={clsx(
                'flex items-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all',
                'focus:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                f.color,
                formaSelecionada === f.key && 'ring-2 ring-offset-1 ring-offset-bg-surface ring-accent',
              )}
            >
              {f.icon}
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input de valor */}
      {formaSelecionada && (
        <div className="flex flex-col gap-2 rounded-lg border border-border bg-bg-surface-2 p-3 animate-slide-in">
          <div className="flex items-center gap-2">
            <DollarSign size={14} className="text-text-muted" />
            <span className="text-sm font-medium text-text-primary">
              Valor para{' '}
              {FORMAS.find((f) => f.key === formaSelecionada)?.label}
            </span>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              value={valorInput}
              onChange={(e) => setValorInput(e.target.value)}
              onFocus={() => onScannerFocusChange(false)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleConfirmarPagamento()
                if (e.key === 'Escape') {
                  setFormaSelecionada(null)
                  onScannerFocusChange(true)
                }
              }}
              placeholder="0,00"
              autoFocus
              className="flex-1 rounded-lg border border-border bg-bg-surface px-3 py-2.5 font-mono text-lg text-text-primary placeholder-text-muted outline-none focus:border-accent/60 focus:ring-2 focus:ring-accent/30"
              inputMode="decimal"
            />
            <Button onClick={handleConfirmarPagamento} loading={loadingPagamento} size="md">
              <Check size={16} />
              OK
            </Button>
          </div>
          {erro && <p className="text-xs text-danger-text">{erro}</p>}
          <p className="text-xs text-text-muted">
            Enter confirma · Esc cancela · Sugerido: {formatCurrency(restante)}
          </p>
        </div>
      )}

      {/* Pagamentos registrados */}
      {venda.pagamentos.length > 0 && (
        <div>
          <p className="mb-1.5 text-xs font-medium uppercase tracking-wider text-text-muted">
            Pagamentos
          </p>
          <ul className="flex flex-col gap-1">
            {venda.pagamentos.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between rounded-lg bg-bg-surface-2 px-3 py-2 text-sm"
              >
                <span className="text-text-secondary">{labelForma(p.forma_pagamento)}</span>
                <span className="font-mono font-medium text-text-primary">
                  {formatCurrency(p.valor)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Botões de finalização */}
      <div className="flex flex-col gap-2">
        {/* F4 — Venda Fiscal (NFC-e) */}
        <Button
          size="xl"
          fullWidth
          onClick={onFinalizarFiscal}
          disabled={!podeFinalizar}
          loading={loadingFinalizar}
          kbd="F4"
          className={clsx(
            modoEmissaoSelecionado === 'FISCAL' && 'ring-2 ring-info/50',
            podeFinalizar && 'animate-pulse-once',
          )}
        >
          {loadingFinalizar ? (
            <Loader2 size={18} className="animate-spin" />
          ) : (
            <Receipt size={18} />
          )}
          Venda Fiscal
        </Button>

        {/* F2 — Pedido Gerencial (sem fiscal) */}
        <Button
          size="lg"
          fullWidth
          variant="secondary"
          onClick={onFinalizarGerencial}
          disabled={!podeFinalizar}
          loading={loadingFinalizar}
          kbd="F2"
          className={clsx(modoEmissaoSelecionado === 'GERENCIAL' && 'ring-2 ring-warning/40')}
        >
          {loadingFinalizar ? (
            <Loader2 size={16} className="animate-spin" />
          ) : (
            <FileText size={16} />
          )}
          Pedido / Gerencial
        </Button>
      </div>

      {!podeFinalizar && venda.itens.filter((i) => !i.cancelado).length > 0 && (
        <p className="text-center text-xs text-danger-text">
          Valor pago insuficiente · Falta {formatCurrency(restante)}
        </p>
      )}
    </div>
  )
}

function labelForma(forma: string): string {
  const map: Record<string, string> = {
    '01': 'Dinheiro',
    '03': 'Cartão Crédito',
    '04': 'Cartão Débito',
    '17': 'Pix',
    '99': 'Outros',
  }
  return map[forma] ?? forma
}
