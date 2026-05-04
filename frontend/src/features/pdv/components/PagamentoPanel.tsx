import { useState } from 'react'
import { DollarSign, QrCode, CreditCard, Banknote, MoreHorizontal, Check, Loader2, FileText, Receipt } from 'lucide-react'
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
  activeColor: string
}

const FORMAS: FormaInfo[] = [
  {
    key: '01',
    label: 'Dinheiro',
    icon: <Banknote size={16} />,
    color: 'border-emerald-800/50 bg-emerald-500/8 hover:bg-emerald-500/15 text-emerald-400',
    activeColor: 'border-emerald-500/60 bg-emerald-500/20 text-emerald-300 ring-1 ring-emerald-500/30',
  },
  {
    key: '17',
    label: 'Pix',
    icon: <QrCode size={16} />,
    color: 'border-blue-800/50 bg-blue-500/8 hover:bg-blue-500/15 text-blue-400',
    activeColor: 'border-blue-500/60 bg-blue-500/20 text-blue-300 ring-1 ring-blue-500/30',
  },
  {
    key: '04',
    label: 'Débito',
    icon: <CreditCard size={16} />,
    color: 'border-violet-800/50 bg-violet-500/8 hover:bg-violet-500/15 text-violet-400',
    activeColor: 'border-violet-500/60 bg-violet-500/20 text-violet-300 ring-1 ring-violet-500/30',
  },
  {
    key: '03',
    label: 'Crédito',
    icon: <CreditCard size={16} />,
    color: 'border-amber-800/50 bg-amber-500/8 hover:bg-amber-500/15 text-amber-400',
    activeColor: 'border-amber-500/60 bg-amber-500/20 text-amber-300 ring-1 ring-amber-500/30',
  },
  {
    key: '99',
    label: 'Outros',
    icon: <MoreHorizontal size={16} />,
    color: 'border-pdv-border bg-pdv-surface-2/50 hover:bg-pdv-surface-2 text-slate-500',
    activeColor: 'border-slate-500/50 bg-slate-700 text-slate-300 ring-1 ring-slate-500/30',
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
  const isFiscal = modoEmissaoSelecionado === 'FISCAL'

  function handleSelecionarForma(forma: FormaPagamento) {
    setFormaSelecionada(forma)
    onScannerFocusChange(false)
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
    <div className="flex flex-col gap-3">

      {/* ══ TIPO DE FINALIZAÇÃO ══ */}
      <div className="rounded-xl border border-pdv-border bg-pdv-surface/60 p-3">
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-600">
          Tipo de Finalização
        </p>
        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => onSelecionarModoEmissao('FISCAL')}
            className={clsx(
              'rounded-lg border px-3 py-2.5 text-left transition-all',
              isFiscal
                ? 'border-emerald-600/60 bg-emerald-500/15 text-emerald-300 shadow-sm shadow-emerald-500/10'
                : 'border-pdv-border bg-pdv-bg/50 hover:bg-pdv-surface text-slate-500 hover:text-slate-400',
            )}
          >
            <div className="flex items-center gap-2 text-sm font-bold">
              <Receipt size={14} />
              Fiscal
            </div>
            <p className="mt-0.5 text-xs opacity-70">Gera NFC-e</p>
          </button>
          <button
            type="button"
            onClick={() => onSelecionarModoEmissao('GERENCIAL')}
            className={clsx(
              'rounded-lg border px-3 py-2.5 text-left transition-all',
              !isFiscal
                ? 'border-amber-600/60 bg-amber-500/15 text-amber-300 shadow-sm shadow-amber-500/10'
                : 'border-pdv-border bg-pdv-bg/50 hover:bg-pdv-surface text-slate-500 hover:text-slate-400',
            )}
          >
            <div className="flex items-center gap-2 text-sm font-bold">
              <FileText size={14} />
              Gerencial
            </div>
            <p className="mt-0.5 text-xs opacity-70">Sem valor fiscal</p>
          </button>
        </div>
      </div>

      {/* ══ FORMA DE PAGAMENTO ══ */}
      <div>
        <p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-slate-600">
          Forma de Pagamento
        </p>
        <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
          {FORMAS.map((f) => (
            <button
              key={f.key}
              onClick={() => handleSelecionarForma(f.key)}
              className={clsx(
                'flex items-center gap-2 rounded-lg border px-2.5 py-2 text-sm font-medium transition-all',
                'focus:outline-none',
                formaSelecionada === f.key ? f.activeColor : f.color,
              )}
            >
              {f.icon}
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {/* ══ INPUT DE VALOR ══ */}
      {formaSelecionada && (
        <div className="flex flex-col gap-2 rounded-lg border border-pdv-border-2 bg-pdv-surface p-3 animate-slide-in">
          <div className="flex items-center gap-2">
            <DollarSign size={13} className="text-slate-500" />
            <span className="text-sm font-medium text-slate-300">
              Valor · {FORMAS.find((f) => f.key === formaSelecionada)?.label}
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
              className="flex-1 rounded-lg border border-pdv-border-2 bg-pdv-bg px-3 py-2.5 font-mono text-xl font-bold text-slate-100 placeholder-slate-700 outline-none focus:border-emerald-600/60 focus:ring-1 focus:ring-emerald-600/30"
              inputMode="decimal"
            />
            <button
              onClick={handleConfirmarPagamento}
              disabled={loadingPagamento}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 px-4 py-2 font-semibold text-white transition-colors disabled:opacity-50"
            >
              {loadingPagamento ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} />}
              OK
            </button>
          </div>
          {erro && <p className="text-xs text-red-400">{erro}</p>}
          <p className="text-xs text-slate-600">Enter confirma · Esc cancela · Sug.: {formatCurrency(restante)}</p>
        </div>
      )}

      {/* ══ PAGAMENTOS REGISTRADOS ══ */}
      {venda.pagamentos.length > 0 && (
        <div>
          <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-600">
            Pagamentos
          </p>
          <ul className="flex flex-col gap-1">
            {venda.pagamentos.map((p) => (
              <li
                key={p.id}
                className="flex items-center justify-between rounded-lg border border-pdv-border bg-pdv-surface px-3 py-2 text-sm"
              >
                <span className="text-slate-500">{labelForma(p.forma_pagamento)}</span>
                <span className="font-mono font-semibold text-emerald-400">
                  + {formatCurrency(p.valor)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* ══ BOTÕES DE FINALIZAÇÃO — MODO-RESPONSIVOS ══ */}
      <div className="flex flex-col gap-2 pt-1">
        {isFiscal ? (
          <>
            {/* FISCAL modo → "Venda Fiscal" é o botão primário grande */}
            <button
              onClick={onFinalizarFiscal}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-3 rounded-xl px-4 py-4 font-bold text-base transition-all duration-200',
                podeFinalizar
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 hover:shadow-emerald-500/40'
                  : 'bg-pdv-surface border border-pdv-border text-slate-600 cursor-not-allowed',
              )}
            >
              {loadingFinalizar ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <Receipt size={20} />
              )}
              <span>Venda Fiscal</span>
              <kbd className="ml-auto rounded bg-white/15 px-2 py-0.5 font-mono text-sm">F4</kbd>
            </button>
            {/* Pedido/Gerencial — botão secundário menor */}
            <button
              onClick={onFinalizarGerencial}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all',
                podeFinalizar
                  ? 'border-pdv-border-2 bg-pdv-surface hover:bg-pdv-surface-2 text-slate-400 hover:text-slate-300'
                  : 'border-pdv-border/50 bg-transparent text-slate-700 cursor-not-allowed',
              )}
            >
              <FileText size={15} />
              Pedido / Gerencial
              <kbd className="ml-auto rounded border border-pdv-border bg-pdv-bg px-1.5 py-0.5 font-mono text-xs text-slate-600">F2</kbd>
            </button>
          </>
        ) : (
          <>
            {/* GERENCIAL modo → "Pedido / Gerencial" é o botão primário grande */}
            <button
              onClick={onFinalizarGerencial}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-3 rounded-xl px-4 py-4 font-bold text-base transition-all duration-200',
                podeFinalizar
                  ? 'bg-amber-500 hover:bg-amber-400 text-white shadow-lg shadow-amber-500/30 hover:shadow-amber-400/40'
                  : 'bg-pdv-surface border border-pdv-border text-slate-600 cursor-not-allowed',
              )}
            >
              {loadingFinalizar ? (
                <Loader2 size={20} className="animate-spin" />
              ) : (
                <FileText size={20} />
              )}
              <span>Pedido / Gerencial</span>
              <kbd className="ml-auto rounded bg-white/15 px-2 py-0.5 font-mono text-sm">F2</kbd>
            </button>
            {/* Venda Fiscal — botão secundário menor */}
            <button
              onClick={onFinalizarFiscal}
              disabled={!podeFinalizar || loadingFinalizar}
              className={clsx(
                'flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2.5 text-sm font-medium transition-all',
                podeFinalizar
                  ? 'border-pdv-border-2 bg-pdv-surface hover:bg-pdv-surface-2 text-slate-400 hover:text-slate-300'
                  : 'border-pdv-border/50 bg-transparent text-slate-700 cursor-not-allowed',
              )}
            >
              <Receipt size={15} />
              Venda Fiscal
              <kbd className="ml-auto rounded border border-pdv-border bg-pdv-bg px-1.5 py-0.5 font-mono text-xs text-slate-600">F4</kbd>
            </button>
          </>
        )}
      </div>

      {!podeFinalizar && venda.itens.filter((i) => !i.cancelado).length > 0 && (
        <p className="text-center text-xs text-red-500">
          Falta {formatCurrency(restante)} para finalizar
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

